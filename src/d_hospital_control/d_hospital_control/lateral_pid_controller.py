#!/usr/bin/env python3
"""
lateral_pid_controller
-----------------------
Controlador PID de malha fechada para corrigir o erro lateral (e_y) de um
robô diferencial em movimento reto, usando a odometria (/odom) como
realimentação e publicando correções de velocidade angular em /cmd_vel.

Problema que este nó resolve:
    Em malha aberta (apenas linear.x constante, angular.z = 0), o robô
    acumula um pequeno desvio lateral sistemático (curva sempre para o
    mesmo lado) devido a assimetrias físicas/numéricas da simulação ou
    do hardware real. Este nó fecha a malha: mede o erro lateral e de
    rumo (yaw) a cada ciclo de controle e aplica uma correção angular
    proporcional-integral-derivativa para manter o robô na reta de
    referência.

Lei de controle:
    e_y   = y_referencia - y_atual                  (erro lateral, m)
    saida = Kp*e_y + Ki*integral(e_y) + Kd*d(e_y)/dt
    angular.z = saturar(saida, -max_angular_z, max_angular_z)

    Um termo adicional de amortecimento por rumo (heading damping) é
    somado para reduzir oscilação: Kh * (0 - yaw_atual).

A referência de linha reta (y_referencia, yaw_referencia) é capturada
automaticamente na primeira leitura de /odom, então o nó funciona a
partir de qualquer pose inicial do robô.
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from std_srvs.srv import Empty


def quaternion_to_yaw(q):
    """Extrai o ângulo de yaw (rotação em torno de Z) de um quaternion."""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class LateralPidController(Node):

    def __init__(self):
        super().__init__('lateral_pid_controller')

        # --- Parâmetros ROS2 (ajustáveis via CLI, launch ou yaml) ---
        self.declare_parameter('linear_velocity', 0.25)      # m/s
        self.declare_parameter('kp', 0.8)                    # ganho proporcional (e_y)
        self.declare_parameter('ki', 0.0)                     # ganho integral (e_y)
        self.declare_parameter('kd', 0.15)                    # ganho derivativo (e_y)
        self.declare_parameter('kh', 0.6)                     # ganho de amortecimento de rumo (yaw)
        self.declare_parameter('max_angular_z', 0.5)          # rad/s, saturação de saída
        self.declare_parameter('integral_limit', 0.5)         # anti-windup do termo integral
        self.declare_parameter('control_frequency', 30.0)     # Hz (bate com update_rate do controller_manager)
        self.declare_parameter('goal_distance', 0.0)          # m; 0.0 = desativado (roda indefinidamente)
        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')

        self.v_cmd = self.get_parameter('linear_velocity').value
        self.kp = self.get_parameter('kp').value
        self.ki = self.get_parameter('ki').value
        self.kd = self.get_parameter('kd').value
        self.kh = self.get_parameter('kh').value
        self.max_ang = self.get_parameter('max_angular_z').value
        self.integral_limit = self.get_parameter('integral_limit').value
        freq = self.get_parameter('control_frequency').value
        self.goal_distance = self.get_parameter('goal_distance').value
        odom_topic = self.get_parameter('odom_topic').value
        cmd_vel_topic = self.get_parameter('cmd_vel_topic').value

        # --- Estado interno do controlador ---
        self.y_ref = None
        self.yaw_ref = None
        self.x0 = None
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_yaw = 0.0
        self.have_odom = False

        self.integral_term = 0.0
        self.prev_error = 0.0
        self.prev_time = None
        self.goal_reached = False

        # --- Publisher / Subscriber / Timer ---
        qos = QoSProfile(depth=10)
        self.cmd_pub = self.create_publisher(Twist, cmd_vel_topic, qos)
        self.odom_sub = self.create_subscription(
            Odometry, odom_topic, self.odom_callback, qos)

        self.control_timer = self.create_timer(1.0 / freq, self.control_loop)

        # Serviço opcional para reiniciar o controlador (útil entre amostras
        # de experimento, análogo ao /reset_simulation usado no experimento.sh)
        self.reset_srv = self.create_service(
            Empty, 'lateral_pid_controller/reset', self.reset_callback)

        self.get_logger().info(
            f'lateral_pid_controller iniciado | v={self.v_cmd:.3f} m/s | '
            f'Kp={self.kp} Ki={self.ki} Kd={self.kd} Kh={self.kh} | '
            f'odom_topic={odom_topic} cmd_vel_topic={cmd_vel_topic}'
        )

    # ------------------------------------------------------------------
    def odom_callback(self, msg: Odometry):
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
        self.current_yaw = quaternion_to_yaw(msg.pose.pose.orientation)

        if not self.have_odom:
            # Captura a reta de referência a partir da primeira leitura
            self.y_ref = self.current_y
            self.yaw_ref = self.current_yaw
            self.x0 = self.current_x
            self.have_odom = True
            self.get_logger().info(
                f'Referência capturada: y_ref={self.y_ref:.4f} '
                f'yaw_ref={math.degrees(self.yaw_ref):.2f} graus'
            )

    # ------------------------------------------------------------------
    def control_loop(self):
        if not self.have_odom or self.goal_reached:
            return

        now = self.get_clock().now()
        if self.prev_time is None:
            dt = 1.0 / self.get_parameter('control_frequency').value
        else:
            dt = (now - self.prev_time).nanoseconds * 1e-9
            if dt <= 0.0:
                dt = 1.0 / self.get_parameter('control_frequency').value
        self.prev_time = now

        # --- Cálculo dos erros ---
        e_y = self.y_ref - self.current_y
        e_yaw = self.yaw_ref - self.current_yaw
        # normaliza e_yaw para [-pi, pi]
        e_yaw = math.atan2(math.sin(e_yaw), math.cos(e_yaw))

        # --- Termo integral com anti-windup ---
        self.integral_term += e_y * dt
        self.integral_term = max(-self.integral_limit,
                                  min(self.integral_limit, self.integral_term))

        # --- Termo derivativo ---
        derivative = (e_y - self.prev_error) / dt if dt > 0 else 0.0
        self.prev_error = e_y

        # --- Lei de controle PID + amortecimento de rumo ---
        # Os termos derivados de e_y (P, I, D) precisam ser multiplicados
        # pelo sentido do movimento: corrigir um desvio lateral exige
        # esterçar para o lado oposto quando o robô anda de ré (mesma
        # lógica de "contra-esterçar" ao dar ré num carro). O termo de
        # rumo (Kh*e_yaw) NÃO precisa disso: a dinâmica do yaw em relação
        # a angular.z independe do sentido do movimento linear.
        direction = 1.0 if self.v_cmd >= 0.0 else -1.0
        angular_z = (direction * (self.kp * e_y
                                   + self.ki * self.integral_term
                                   + self.kd * derivative)
                     + self.kh * e_yaw)

        angular_z = max(-self.max_ang, min(self.max_ang, angular_z))

        # --- Checagem de meta de distância (opcional) ---
        if self.goal_distance > 0.0:
            dist = abs(self.current_x - self.x0)
            if dist >= self.goal_distance:
                self.goal_reached = True
                self.publish_cmd(0.0, 0.0)
                self.get_logger().info(
                    f'Meta de distância atingida ({dist:.3f} m). Parando.'
                )
                return

        self.publish_cmd(self.v_cmd, angular_z)

        self.get_logger().debug(
            f'e_y={e_y:+.4f} e_yaw={math.degrees(e_yaw):+.2f} '
            f'-> angular.z={angular_z:+.4f}'
        )

    # ------------------------------------------------------------------
    def publish_cmd(self, linear_x, angular_z):
        msg = Twist()
        msg.linear.x = linear_x
        msg.angular.z = angular_z
        self.cmd_pub.publish(msg)

    # ------------------------------------------------------------------
    def reset_callback(self, request, response):
        self.have_odom = False
        self.integral_term = 0.0
        self.prev_error = 0.0
        self.prev_time = None
        self.goal_reached = False
        self.get_logger().info('Controlador reiniciado, aguardando nova referência.')
        return response


def main(args=None):
    rclpy.init(args=args)
    node = LateralPidController()
    try:
        # Loop manual em vez de rclpy.spin(node): permite encerrar o
        # processo sozinho assim que a meta de distância for atingida
        # (útil para scripts de experimento em lote). Se goal_distance=0
        # o nó nunca marca goal_reached e o comportamento é o mesmo de
        # antes (roda até Ctrl+C).
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
            if node.goal_reached and node.goal_distance > 0.0:
                # pequena folga para garantir que o /cmd_vel=0 foi publicado
                # e processado antes de derrubar o nó
                for _ in range(3):
                    rclpy.spin_once(node, timeout_sec=0.1)
                node.get_logger().info('Meta atingida, encerrando o nó.')
                break
    except KeyboardInterrupt:
        pass
    finally:
        node.publish_cmd(0.0, 0.0)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
