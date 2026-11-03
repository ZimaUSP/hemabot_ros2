#!/usr/bin/env python3
"""Expand variants and verify actual URDF physics/frames/assets, without ROS."""
import argparse
import itertools
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import xacro
import yaml

PKG=Path(__file__).resolve().parents[1]


def vector(text):
    return np.array([float(v) for v in text.split()])


def check(root, backend, interface, articulated, model):
    links={e.get('name'):e for e in root.findall('link')}
    joints={e.get('name'):e for e in root.findall('joint')}
    assert len(links)==17 and len(joints)==16
    children=[j.find('child').get('link') for j in joints.values()]
    assert len(set(children))==len(children)
    assert set(links)-set(children)=={'base_link'}
    poses={'base_link':np.zeros(3)}
    for _ in range(len(joints)):
        for j in joints.values():
            parent=j.find('parent').get('link');child=j.find('child').get('link')
            assert parent in links and child in links
            if parent in poses:
                poses[child]=poses[parent]+vector(j.find('origin').get('xyz'))
    assert len(poses)==len(links), 'Disconnected/cyclic graph'
    total=0.
    for name,link in links.items():
        inertial=link.find('inertial')
        if name=='tool0':
            assert inertial is None
            continue
        mass=float(inertial.find('mass').get('value'));total+=mass
        assert np.isfinite(mass) and mass>0
        a={k:float(v) for k,v in inertial.find('inertia').attrib.items()}
        I=np.array([[a['ixx'],a['ixy'],a['ixz']],[a['ixy'],a['iyy'],a['iyz']],[a['ixz'],a['iyz'],a['izz']]])
        eig=np.linalg.eigvalsh(I)
        assert np.isfinite(eig).all() and eig.min()>0, name
        assert eig[-1]<=eig[0]+eig[1]+1e-9, name
        for mesh in link.findall('visual/geometry/mesh'):
            uri=mesh.get('filename');prefix='package://hema_description/'
            assert uri.startswith(prefix) and (PKG/uri[len(prefix):]).is_file(),uri
            assert mesh.get('scale')=='1 1 1'
        for geom in link.findall('collision/geometry'):
            assert geom.find('mesh') is None
            g=list(geom)[0]
            dims=vector(g.get('size')) if g.tag=='box' else np.array([float(g.get('radius')),float(g.get('length'))])
            assert (dims>0).all()
    cad_mass=sum(v['mass'] for v in model['links'].values())
    lidar_mass=float(links['lidar_link'].find('inertial/mass').get('value'))
    assert abs(total-cad_mass-lidar_mass)<1e-8
    for j in joints.values():
        t=j.get('type')
        if t=='fixed':continue
        assert abs(np.linalg.norm(vector(j.find('axis').get('xyz')))-1)<1e-10
        assert float(j.find('limit').get('effort'))>0
        assert float(j.find('limit').get('velocity'))>0
        assert float(j.find('dynamics').get('damping'))>=0
        if t=='prismatic':
            assert float(j.find('limit').get('lower'))==0
            assert float(j.find('limit').get('upper'))==.25
        if t=='continuous':
            assert j.find('limit').get('lower') is None and j.find('limit').get('upper') is None
    assert sum(j.get('type')=='prismatic' for j in joints.values())==(4 if articulated else 0)
    floor=[]
    for name,pose in poses.items():
        if name.endswith('_wheel_link'):
            radius=float(links[name].find('collision/geometry/cylinder').get('radius'))
            floor.append(pose[2]-radius)
    assert np.ptp(floor)<1e-8, floor
    assert poses['left_wheel_link'][1]>0>poses['right_wheel_link'][1]
    assert abs(poses['left_wheel_link'][1]-poses['right_wheel_link'][1]-model['wheel_separation'])<1e-9
    assert np.allclose(poses['lidar_link'], [-0.1508, 0.0, 0.106], atol=1e-9)
    for name,cfg in model['links'].items():
        original=vector(cfg['origin'])
        if name.startswith('caster_'):original[2]+=model['caster_z_adjust']
        assert np.allclose(poses[name],original,atol=1e-9),name
    control=root.find('ros2_control')
    lidar_sensors=root.findall("gazebo[@reference='lidar_link']/sensor")
    if backend=='none':
        assert control is None and not root.findall('gazebo/plugin') and not lidar_sensors
    else:
        assert control is not None
        controlled=control.findall('joint')
        actuated=[j for j in controlled if j.find('command_interface') is not None]
        assert [j.get('name') for j in actuated]==['left_wheel_joint','right_wheel_joint']
        assert all(j.find('command_interface').get('name')==interface for j in actuated)
        assert len(controlled)==(14 if articulated else 10)
        assert all(j.get('name') in joints for j in controlled)
        assert len(root.findall('gazebo/plugin'))==1
        plugin=root.find('gazebo/plugin').get('filename')
        assert ('libgz_ros2_control-system.so' if backend=='harmonic' else 'libgazebo_ros2_control.so')==plugin
        assert len(lidar_sensors)==1
        sensor=lidar_sensors[0]
        assert sensor.get('type')==('gpu_lidar' if backend=='harmonic' else 'ray')
        ray=sensor.find('lidar') if backend=='harmonic' else sensor.find('ray')
        horizontal=ray.find('scan/horizontal')
        assert int(horizontal.findtext('samples'))==361
        assert np.isclose(float(horizontal.findtext('min_angle')), -np.pi/2)
        assert np.isclose(float(horizontal.findtext('max_angle')), np.pi/2)
        assert np.isclose(float(ray.findtext('range/min')), 0.15)
        assert np.isclose(float(ray.findtext('range/max')), 12.0)
        if backend=='classic':
            assert sensor.find('plugin').get('filename')=='libgazebo_ros_ray_sensor.so'
            assert sensor.findtext('plugin/output_type')=='sensor_msgs/LaserScan'
            assert sensor.findtext('plugin/frame_name')=='lidar_link'
        else:
            assert sensor.findtext('topic')=='scan'
    return total


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=PKG/'generated')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    model=yaml.safe_load((PKG/'config/cad_parameters.yaml').read_text())
    results=[]
    for backend,interface,articulated,inertia in itertools.product(['none','classic','harmonic'],['velocity','position','effort'],[False,True],['mesh','primitive']):
        mappings=dict(backend=backend,command_interface=interface,articulate_slides=str(articulated).lower(),inertia_mode=inertia,
                      controllers_file=str(PKG/'config'/f'controllers_{interface}.yaml'))
        xml=xacro.process_file(str(PKG/'urdf/robot.urdf.xacro'),mappings=mappings).toxml()
        mass=check(ET.fromstring(xml),backend,interface,articulated,model)
        if interface=='velocity' and not articulated and inertia=='mesh':
            (args.output/f'robot_{backend}.urdf').write_text(xml,encoding='utf8')
        results.append(dict(backend=backend,interface=interface,slides=articulated,inertia=inertia,pass_=True))
    # Density/mass scaling must scale tensors linearly and preserve the CoM.
    one=ET.fromstring(xacro.process_file(str(PKG/'urdf/robot.urdf.xacro'),mappings={'backend':'none'}).toxml())
    two=ET.fromstring(xacro.process_file(str(PKG/'urdf/robot.urdf.xacro'),mappings={'backend':'none','mass_scale':'2'}).toxml())
    for a,b in zip(one.findall('link/inertial'),two.findall('link/inertial')):
        assert np.isclose(float(b.find('mass').get('value')),2*float(a.find('mass').get('value')))
        assert a.find('origin').attrib==b.find('origin').attrib
        assert all(np.isclose(float(b.find('inertia').get(k)),2*float(v)) for k,v in a.find('inertia').attrib.items())
    report=dict(xacro_version=getattr(xacro,'__version__','see installed distribution'),variants=len(results),mass_kg=mass,links=17,joints=16,checks=results,
                tests=['tree','assets','positive_definite_tensors','principal_moment_triangle','cad_frames','coplanar_contacts','passive_and_actuated_interfaces','lidar_180_degrees','mass_scaling'])
    (args.output/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(f'PASS: {len(results)} variants, 17 links, 16 joints, {mass:.6f} kg; assets, tensors, frames, contacts, LiDAR and control checked.')


if __name__=='__main__':main()
