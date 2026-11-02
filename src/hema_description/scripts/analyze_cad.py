#!/usr/bin/env python3
"""Reproduce CAD measurements/assets from the user's ZIP (never execute archive files).

Dependencies: numpy, trimesh, scipy, PyYAML. STL coordinates are mm in a common
assembly frame. Materials are engineering assumptions, not CAD metadata.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import defaultdict
import numpy as np
import trimesh
import yaml

PKG = Path(__file__).resolve().parents[1]
R = np.array([[0., 0., -1.], [-1., 0., 0.], [0., 1., 0.]])
DENSITIES = {'aluminium': 2700., 'steel': 7850., 'abs': 1040.,
             'pla': 1240., 'rubber': 1100., 'nylon': 1150.,
             'electronics': 1800., 'motor_composite': 3000.}


def vec(v):
    return ' '.join(f'{x:.10g}' for x in v)


def classify(name, center):
    side = 'left' if center[1] > 0 else 'right'
    corner = ('front_' if center[0] > 0 else 'rear_') + side
    if 'Hoverboardwheel' in name:
        return f'{side}_wheel_link', 'motor_composite'
    if 'roda.STEP' in name and 'eixo_roda' not in name:
        return f'caster_{corner}_wheel_link', 'nylon'
    if 'eixo_roda' in name or ' Suporte.STEP' in name:
        return f'caster_{corner}_fork_link', 'steel'
    if 'CORREDICA_DO_MEIO' in name:
        return f'slide_{side}_middle_link', 'steel'
    if 'CORREDICA_INTERNO' in name:
        return f'slide_{side}_inner_link', 'steel'
    if any(t in name for t in ['Parafuso', 'Porca', 'CORREDICA', 'base.STEP']):
        return 'base_link', 'steel'
    if any(t in name for t in ['Perfil', 'CANTONEIRA', 'Suporte_do_motor']):
        return 'base_link', 'aluminium'
    if 'Suporte_do_Rod' in name:
        return 'base_link', 'steel'
    if 'Carenagem' in name or 'Acabamento' in name:
        return 'base_link', 'pla'
    if 'Sensor_Ultrass' in name:
        return 'base_link', 'electronics'
    if any(t in name for t in ['Spring', 'spring', ' axis.', 'nut.STEP', 'M3F']):
        return 'base_link', 'steel'
    return 'base_link', 'abs'


def analyze(archive):
    for d in ['meshes', 'config', 'docs', 'urdf']:
        (PKG / d).mkdir(parents=True, exist_ok=True)
    records, assets, models = [], defaultdict(list), {}
    with zipfile.ZipFile(archive) as z:
        files = sorted(n for n in z.namelist() if '/HEMA.stl/' in n and n.lower().endswith('.stl'))
        meshes = {n: trimesh.load(io.BytesIO(z.read(n)), file_type='stl', force='mesh') for n in files}
        wheels = [m for n, m in meshes.items() if 'Hoverboardwheel' in n]
        origin_mm = np.mean([m.bounds.mean(0) for m in wheels], axis=0)
        # Origin: midpoint of wheel axle, not midpoint of tire bounding boxes.
        T = np.eye(4); T[:3,:3] = R * .001; T[:3,3] = -R @ origin_mm * .001
        for m in meshes.values():
            m.apply_transform(T)
        frames = {'base_link': np.zeros(3)}
        wheel_radius = float(wheels[0].extents[2] / 2)
        tire_centers, tire_widths = [], []
        for name, m in meshes.items():
            center = m.bounds.mean(0)
            link, mat = classify(name, center)
            if 'Hoverboardwheel' in name:
                radius = np.linalg.norm(m.vertices[:,[0,2]] - center[[0,2]], axis=1)
                tire = m.vertices[radius > radius.max() * .95]
                tire_center = (tire.max(0) + tire.min(0))/2
                frames[link] = tire_center
                tire_centers.append(tire_center); tire_widths.append(float(np.ptp(tire[:,1])))
            if 'roda.STEP' in name and 'eixo_roda' not in name:
                frames[link] = center
            if ' base.STEP' in name and 'Girat' in name:
                side = 'left' if center[1] > 0 else 'right'
                corner = ('front_' if center[0] > 0 else 'rear_') + side
                frames[f'caster_{corner}_fork_link'] = center - [0,0,m.extents[2]/2]
            if link.startswith('slide_'):
                frames[link] = center
        for name, m in meshes.items():
            link, mat = classify(name, m.bounds.mean(0))
            raw_closed = bool(m.is_watertight)
            physical = m.copy()
            method = 'closed_stl'
            if not raw_closed:
                # Only triangle/quad hole filling for wheels; no guessed major surfaces.
                if 'Hoverboardwheel' in name:
                    trimesh.repair.fill_holes(physical)
                    method = 'closed_stl_small_holes_repaired'
                if not physical.is_watertight:
                    physical = m.convex_hull
                    method = 'convex_hull_proxy_open_stl'
            if physical.volume <= 0:
                physical.invert()
            density = DENSITIES[mat]
            physical.density = density
            p = physical.mass_properties
            mass, com, tensor = float(p.mass), np.array(p.center_mass), np.array(p.inertia)
            if mass <= 0 or np.linalg.eigvalsh(tensor).min() <= 0:
                raise ValueError(f'Invalid mass properties: {name}')
            records.append(dict(source=name, link=link, material=mat, density_kg_m3=density,
                raw_watertight=raw_closed, volume_method=method, volume_m3=float(physical.volume),
                mass_kg=mass, com_base_m=com.tolist(), inertia_com_kg_m2=tensor.tolist(),
                bounds_base_m=m.bounds.tolist(), triangles=len(m.faces)))
            assets[(link, mat)].append(m)
        for link, frame in frames.items():
            parts = [r for r in records if r['link'] == link]
            mass = sum(r['mass_kg'] for r in parts)
            com = sum(r['mass_kg'] * np.array(r['com_base_m']) for r in parts) / mass
            inertia = np.zeros((3,3))
            for r in parts:
                delta = np.array(r['com_base_m'])-com
                inertia += np.array(r['inertia_com_kg_m2']) + r['mass_kg']*(delta@delta*np.eye(3)-np.outer(delta,delta))
            lo = np.min([r['bounds_base_m'][0] for r in parts],axis=0)-frame
            hi = np.max([r['bounds_base_m'][1] for r in parts],axis=0)-frame
            models[link] = dict(mass=mass, com=vec(com-frame), origin=vec(frame),
                ixx=float(inertia[0,0]), ixy=float(inertia[0,1]), ixz=float(inertia[0,2]),
                iyy=float(inertia[1,1]), iyz=float(inertia[1,2]), izz=float(inertia[2,2]),
                box_size=vec(hi-lo), box_center=vec((hi+lo)/2), materials=sorted({r['material'] for r in parts}),
                meshes=[])
        for (link, material), items in sorted(assets.items()):
            asset = trimesh.util.concatenate(items)
            asset.apply_translation(-frames[link])
            filename = f'{link}_{material}.stl'
            asset.export(PKG/'meshes'/filename)
            models[link]['meshes'].append(dict(file=filename,material='hema_rubber' if material=='motor_composite' else 'hema_'+material))
        caster_radius = .025
        caster_bottom = frames['caster_front_left_wheel_link'][2] - caster_radius
        caster_adjust = -wheel_radius - caster_bottom
        for corner in ['front_left','front_right','rear_left','rear_right']:
            fork = f'caster_{corner}_fork_link'; wheel=f'caster_{corner}_wheel_link'
            models[wheel]['joint_origin'] = vec(frames[wheel]-frames[fork])
        for side in ['left','right']:
            middle=f'slide_{side}_middle_link'; inner=f'slide_{side}_inner_link'
            models[inner]['joint_origin'] = vec(frames[inner]-frames[middle])
        model = dict(source_sha256=hashlib.sha256(Path(archive).read_bytes()).hexdigest(),
            source_meshes=len(files), cad_origin_mm=origin_mm.tolist(), cad_to_ros_rotation=R.tolist(),
            wheel_radius=wheel_radius, wheel_width=float(np.mean(tire_widths)),
            wheel_separation=float(abs(tire_centers[0][1]-tire_centers[1][1])),
            caster_radius=caster_radius, caster_width=.0228, caster_z_adjust=float(caster_adjust),
            links=models)
        (PKG/'config/cad_parameters.yaml').write_text(yaml.safe_dump(model,sort_keys=False),encoding='utf8')
        (PKG/'docs/cad_parts.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
        with (PKG/'docs/cad_parts.csv').open('w',encoding='utf-8-sig',newline='') as f:
            keys=['source','link','material','density_kg_m3','raw_watertight','volume_method','volume_m3','mass_kg']
            w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(records)
        (PKG/'docs/reference.png').write_bytes(z.read('Hema_V4/Foto.png'))
        inventory=[dict(path=i.filename,bytes=i.file_size,used=i.filename in files) for i in z.infolist() if not i.is_dir()]
        (PKG/'docs/archive_inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf8')
    # Visual instances are generated independently of the hand-maintained kinematics.
    lines=['<?xml version="1.0"?>','<robot xmlns:xacro="http://www.ros.org/wiki/xacro">']
    for link,cfg in models.items():
        lines.append(f'  <xacro:macro name="visuals_{link}" params="">')
        for asset in cfg['meshes']:
            lines.extend(['    <visual>',f'      <geometry><mesh filename="package://hema_description/meshes/{asset["file"]}" scale="1 1 1"/></geometry>',f'      <material name="{asset["material"]}"/>','    </visual>'])
        lines.append('  </xacro:macro>')
    lines.append('</robot>')
    (PKG/'urdf/cad_visuals.xacro').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps({'links':len(models),'parts':len(records),'mass_kg':sum(r['mass_kg'] for r in records),
        'raw_closed':sum(r['raw_watertight'] for r in records),'methods':dict((m,sum(r['volume_method']==m for r in records)) for m in sorted({r['volume_method'] for r in records})),
        'wheel_radius':wheel_radius,'wheel_width':model['wheel_width'],'wheel_separation':model['wheel_separation'],'caster_z_adjust':caster_adjust},indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path)
    analyze(parser.parse_args().archive)
