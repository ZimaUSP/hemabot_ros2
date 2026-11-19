# firmware_minihema

## Arquivos

- `DEV_Config.h` — Declara tipos e macros usados para acessar a placa e seus periféricos.
- `KeyesDriver.h` — Declara as funções usadas para acionar o driver Keyes dos motores.
- `PinPlannerRasp.h` — Centraliza a identificação dos pinos do Raspberry Pi usados pelo firmware.
- `minihema_hardware.hpp` — Declara a interface ros2_control dos motores, com controle PID e ajustes de leitura dos encoders.
- `motor_encoder.h` — Declara a leitura das contagens e dos instantes dos pulsos dos encoders e o envio de comandos aos motores.
- `wheel.hpp` — Declara a classe que calcula a posição e a velocidade da roda com filtro e timeout dos pulsos.
- `pid.hpp` — Declara o controlador PID e seus parâmetros de ganho, integração e limite de saída.
