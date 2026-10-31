#!/usr/bin/env python3
"""
HemaBot API Server
Servidor HTTP que expõe comandos do robô para o app Android.
Roda em paralelo com o ROS2 usando threading.

Instalação: pip install fastapi uvicorn
Porta: 8000 (liberar no firewall: sudo ufw allow 8000/tcp)
"""

import os
import signal
import subprocess
import threading
import asyncio

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="HemaBot API", version="1.0.0")

# Nó ROS2 global — inicializado na thread de background
_ros_node: Node = None
_ros_lock = threading.Lock()

# PIDs dos processos ROS2 lançados pelo app
_launched_processes: dict[str, subprocess.Popen] = {}


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/robot/status")
async def get_status():
    """Retorna os nós ROS2 ativos e se o servidor está online."""
    try:
        result = subprocess.run(
            ["ros2", "node", "list"],
            capture_output=True, text=True, timeout=5
        )
        nodes = [n for n in result.stdout.strip().split("\n") if n]
        return {
            "online": True,
            "active_nodes": nodes,
            "launched_processes": list(_launched_processes.keys())
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"online": False, "error": str(e)})


@app.post("/robot/initialize")
async def initialize_robot():
    """
    Lança o minihema_launch.py completo (motores, sensores, localização).
    Se já estiver rodando, retorna status 'already_running'.
    """
    if "minihema" in _launched_processes:
        proc = _launched_processes["minihema"]
        if proc.poll() is None:  # ainda rodando
            return {"status": "already_running", "message": "Robô já está inicializado"}

    try:
        log_start = open("/home/hemabot/hemabot_ros2/hema_start.log", "w")
        proc = subprocess.Popen(
            ["/home/hemabot/hemabot_ros2/start_hema.sh"],
            stdout=log_start,
            stderr=log_start
        )
        _launched_processes["minihema"] = proc
        return {"status": "launching", "pid": proc.pid, "message": "Inicialização do robô em andamento"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/robot/checks")
async def run_motor_checks():
    """
    Chama o serviço ROS2 /checks para testar os motores.
    Requer que o robô já esteja inicializado (minihema_launch).
    """
    node = _ros_node
    if node is None:
        return JSONResponse(status_code=503, content={
            "success": False,
            "message": "Nó ROS2 não está pronto. Inicialize o robô primeiro."
        })

    try:
        client = node.create_client(Trigger, "/checks")

        if not client.wait_for_service(timeout_sec=5.0):
            node.destroy_client(client)
            return JSONResponse(status_code=503, content={
                "success": False,
                "message": "Serviço /checks não disponível. O robô está inicializado?"
            })

        future = client.call_async(Trigger.Request())

        # Aguarda resposta sem bloquear o event loop do asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: _wait_for_future(future))
        node.destroy_client(client)

        return {"success": result.success, "message": result.message}

    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@app.post("/robot/slam/start")
async def start_slam():
    """
    Inicia o SLAM (mapeamento simultâneo) usando slam_toolbox.
    Use para criar ou atualizar o mapa do ambiente.
    """
    if "slam" in _launched_processes:
        proc = _launched_processes["slam"]
        if proc.poll() is None:
            return {"status": "already_running", "message": "SLAM já está ativo"}

    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        slam_log = open("/home/hemabot/hemabot_ros2/slam.log", "w")
        proc = subprocess.Popen(
            "source /opt/ros/humble/setup.bash && "
            "source /home/hemabot/hemabot_ros2/install/setup.bash && "
            "ros2 launch d_hospital_slam online_async_launch.py "
            "slam_params_file:=src/d_hospital_slam/config/mapper_params_online_async.yaml "
            "use_sim_time:=false",
            shell=True,
            cwd="/home/hemabot/hemabot_ros2",
            stdout=slam_log,
            stderr=slam_log,
            env=env
        )
        _launched_processes["slam"] = proc
        return {"status": "started", "pid": proc.pid, "message": "SLAM iniciado"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/robot/shutdown")
async def shutdown_robot():
    """
    Encerra os processos ROS2 lançados pelo app.
    """
    stopped = []
    for name, proc in list(_launched_processes.items()):
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            stopped.append(name)
        del _launched_processes[name]

    return {"status": "stopped", "stopped_processes": stopped}


# ─────────────────────────────────────────────
# INICIALIZAÇÃO ROS2 (thread de background)
# ─────────────────────────────────────────────

def _wait_for_future(future):
    """Aguarda um future ROS2 de forma síncrona (para uso com run_in_executor)."""
    import time
    while not future.done():
        time.sleep(0.05)
    return future.result()


def _run_ros():
    """Inicializa rclpy e mantém o nó ROS2 rodando em background."""
    global _ros_node
    rclpy.init()
    _ros_node = rclpy.create_node("hemabot_api_node")
    _ros_node.get_logger().info("HemaBot API Node iniciado")
    rclpy.spin(_ros_node)
    _ros_node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    # Inicia ROS2 em thread de background
    ros_thread = threading.Thread(target=_run_ros, daemon=True)
    ros_thread.start()

    # Inicia servidor HTTP na porta 8000
    # host="0.0.0.0" aceita conexões de qualquer IP na rede local
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

