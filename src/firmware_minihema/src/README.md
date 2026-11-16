# src

## Arquivos

- `.motor_test.cpp.swn` — Arquivo temporário de recuperação criado pelo Vim durante a edição.
- `.motor_test.cpp.swo` — Arquivo temporário de recuperação criado pelo Vim durante a edição.
- `KeyesDriver.c` — Implementa o acionamento dos motores pelo driver Keyes.
- `minihema_hardware.cpp` — Lê os encoders e envia os comandos de velocidade aos motores pelo ros2_control.
- `motor_checks_client.cpp` — Chama o serviço ROS 2 `checks` e mostra o resultado da checagem dos motores.
- `motor_checks_server.cpp` — Implementa um servidor ROS 2 `checks` que executa a checagem dos motores.
- `motor_encoder.c` — Conta os pulsos dos encoders para acompanhar o movimento das rodas.
- `motor_stop.c` — Executa o comando de parada dos motores.
- `motor_test.cpp` — Implementa o executável de teste dos motores, que oferece o serviço ROS 2 `checks`.
- `wheel.cpp` — Implementa a conversão de contagens do encoder em posição angular da roda.
