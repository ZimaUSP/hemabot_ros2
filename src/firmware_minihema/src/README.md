# src

## Arquivos

- `.motor_test.cpp.swo` — Arquivo temporário de recuperação criado pelo Vim durante a edição.
- `KeyesDriver.c` — Implementa o acionamento dos motores pelo driver Keyes.
- `minihema_hardware.cpp` — Integra os motores ao ros2_control, lê os encoders e corrige a velocidade com PID e compensação entre rodas.
- `motor_checks_client.cpp` — Chama o serviço ROS 2 `checks` e mostra o resultado da checagem dos motores.
- `motor_checks_server.cpp` — Implementa um servidor ROS 2 `checks` que executa a checagem dos motores.
- `motor_encoder.c` — Registra contagens e instantes dos pulsos dos encoders e converte os comandos das rodas em acionamento dos motores.
- `motor_stop.c` — Executa o comando de parada dos motores.
- `motor_test.cpp` — Executa uma sequência de movimentos e mostra as contagens dos encoders antes e depois de cada teste.
- `wheel.cpp` — Calcula a posição angular e estima a velocidade pelos pulsos do encoder, aplicando filtro e timeout.
- `pid.cpp` — Calcula a correção PID a partir do erro entre a velocidade desejada e a medida, com limites de integração e saída.
- `test_encoder.c` — Mostra as contagens e taxas de pulsos dos encoders enquanto as rodas são giradas manualmente.
