#!/usr/bin/env python3
"""
move_by_distance.py

Move o robô a uma velocidade linear constante até percorrer uma
distância alvo, usando a pose REAL (ground truth) como critério de
parada, em vez de um tempo calculado a priori (distancia / velocidade).

Isso evita que erros de rampa de aceleração, atraso do controlador,
patinagem de roda ou correção lateral do firmware façam o robô parar
antes/depois da distância desejada.

Uso:
    python3 move_by_distance.py --vel -0.25 --distancia 5.0

Parâmetros opcionais:
    --ground-truth-topic  (default: /ground_truth/state)
    --cmd-vel-topic       (default: /cmd_vel)
    --rate                (Hz de publicação do /cmd_vel, default: 30)
    --timeout-seguranca   (s) tempo máximo absoluto antes de desistir
                          e parar mesmo sem atingir a distância alvo
                          (default: 3x o tempo nominal + 5s de folga)
"""

import argparse
import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry


class MoveByDistance(Node):
    def __init__(self, vel, distancia, gt_topic, cmd_topic, rate_hz, timeout_seguranca):
        super().__init__('move_by_distance')

        self.vel = vel
        self.distancia_alvo = abs(distancia)
        self.timeout_seguranca = timeout_seguranca

        self.start_pos = None
        self.distancia_percorrida = 0.0
        self.tempo_decorrido = 0.0
        self.finalizado = False

        self.cmd_pub = self.create_publisher(Twist, cmd_topic, 10)
        self.gt_sub = self.create_subscription(Odometry, gt_topic, self.gt_callback, 10)

        self.period = 1.0 / rate_hz
        self.timer = self.create_timer(self.period, self.timer_callback)

        self.get_logger().info(
            f'Movendo a {self.vel} m/s até percorrer {self.distancia_alvo:.4f} m '
            f'(critério de parada: distância real via {gt_topic}; '
            f'timeout de segurança: {self.timeout_seguranca:.1f} s)'
        )

    def gt_callback(self, msg: Odometry):
        pos = msg.pose.pose.position
        if self.start_pos is None:
            self.start_pos = (pos.x, pos.y)
            return
        dx = pos.x - self.start_pos[0]
        dy = pos.y - self.start_pos[1]
        self.distancia_percorrida = math.hypot(dx, dy)

    def timer_callback(self):
        if self.finalizado:
            return

        self.tempo_decorrido += self.period

        if self.tempo_decorrido >= self.timeout_seguranca:
            self.get_logger().warn(
                f'Timeout de segurança atingido ({self.timeout_seguranca:.1f}s) '
                f'sem alcançar a distância alvo. Distância percorrida: '
                f'{self.distancia_percorrida:.4f} m de {self.distancia_alvo} m. '
                f'Parando mesmo assim.'
            )
            self.parar()
            return

        if self.start_pos is None:
            # ainda não recebemos a primeira pose de ground truth
            return

        if self.distancia_percorrida >= self.distancia_alvo:
            self.parar()
            return

        twist = Twist()
        twist.linear.x = self.vel
        self.cmd_pub.publish(twist)

    def parar(self):
        self.finalizado = True
        stop = Twist()
        for _ in range(5):
            self.cmd_pub.publish(stop)
        self.get_logger().info(
            f'Distância final: {self.distancia_percorrida:.4f} m '
            f'(alvo={self.distancia_alvo} m). Robô parado.'
        )
        self.timer.cancel()
        rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--vel', type=float, required=True,
                         help='Velocidade linear em x (m/s); pode ser negativa')
    parser.add_argument('--distancia', type=float, required=True,
                         help='Distância alvo em metros (sempre positiva)')
    parser.add_argument('--ground-truth-topic', type=str, default='/ground_truth/state')
    parser.add_argument('--cmd-vel-topic', type=str, default='/cmd_vel')
    parser.add_argument('--rate', type=float, default=30.0)
    parser.add_argument('--timeout-seguranca', type=float, default=None,
                         help='Segundos. Default: 3x tempo nominal + 5s')
    args, _ = parser.parse_known_args()

    if args.timeout_seguranca is None:
        tempo_nominal = abs(args.distancia) / abs(args.vel) if args.vel != 0 else 0.0
        args.timeout_seguranca = tempo_nominal * 3 + 5.0

    rclpy.init()
    node = MoveByDistance(
        args.vel, args.distancia,
        args.ground_truth_topic, args.cmd_vel_topic,
        args.rate, args.timeout_seguranca
    )
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()


if __name__ == '__main__':
    main()
