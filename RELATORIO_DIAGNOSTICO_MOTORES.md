# Relatório de diagnóstico dos motores e do desvio lateral

## Objetivo

Este relatório avalia se o desvio lateral observado no robô real pode ser causado ou ampliado pelo código deste repositório, especialmente pelo pequeno atraso percebido entre a ativação dos motores.

## Conclusão executiva

O repositório contém problemas capazes de causar ou ampliar o desvio lateral. Sem medições no protótipo, não é possível afirmar que o software seja a única causa, mas foram encontrados quatro fatores importantes:

1. As rodas são acionadas essencialmente em malha aberta, sem um controlador que iguale suas velocidades reais.
2. A conversão de velocidade para PWM gera comandos extremamente baixos e quantizados, geralmente de 1% a 2% na faixa analisada.
3. Cada motor usa uma thread independente de PWM por software, sem sincronização entre os ciclos.
4. Os dois encoders compartilham incorretamente o mesmo temporizador de debounce, fazendo pulsos de uma roda bloquearem os da outra.

O intervalo entre as chamadas Motor_Run(MOTORA) e Motor_Run(MOTORB) provavelmente é pequeno por si só. Entretanto, combinado com PWM por software, baixo ciclo de trabalho, diferenças de atrito estático e ausência de realimentação, ele pode gerar um erro inicial de orientação que permanece durante toda a trajetória.

## Caminho dos comandos

    /cmd_vel
       ↓
    twist_mux
       ↓
    diff_drive_controller
       ↓
    velocidade angular desejada de cada roda
       ↓
    MinihemaHardware::write()
       ↓
    set_motor_speeds()
       ↓
    Motor_Run(MOTORA)
    Motor_Run(MOTORB)
       ↓
    PWM por software nos GPIOs

Arquivos principais:

- src/minihema_launch/launch/minihema_launch.py
- src/minihema_launch/config/controllers.yaml
- src/firmware_minihema/src/minihema_hardware.cpp
- src/firmware_minihema/src/motor_encoder.c
- src/firmware_minihema/src/KeyesDriver.c

## Problemas encontrados

### 1. Controle de velocidade em malha aberta

Em minihema_hardware.cpp, a velocidade angular solicitada é convertida em uma quantidade estimada de pulsos por ciclo. Em seguida, motor_encoder.c transforma diretamente esse valor em uma porcentagem de acionamento:

    left_motor_speed = ceil(left_wheel_command * 1.65)
    right_motor_speed = ceil(right_wheel_command * 1.65)

Os encoders calculam posição e velocidade publicadas, mas essas velocidades não são comparadas com as velocidades desejadas para corrigir o PWM.

Assim, duas rodas com o mesmo comando podem girar em velocidades diferentes por causa de diferenças entre motores, redutores, rolamentos, pneus, carga, tensão e atrito estático.

### 2. PWM extremamente baixo e quantizado

No robô físico estão configurados:

    update_rate: 30
    wheel_radius: 0.031
    enc_ticks_per_rev: 12
    loop_rate: 30.0

Para um comando reto de 0,25 m/s:

    velocidade angular = 0,25 / 0,031 ≈ 8,06 rad/s
    radianos por pulso = 2π / 12 ≈ 0,524 rad/pulso
    pulsos por ciclo   = 8,06 / 0,524 / 30 ≈ 0,513
    comando calculado  = ceil(0,513 × 1,65) = 1%

| Velocidade linear | PWM calculado |
| ---: | ---: |
| 0,10 m/s | 1% |
| 0,25 m/s | 1% |
| 0,26 m/s | 1% |
| 0,40 m/s | 2% |

Isso sugere incompatibilidade de unidades ou calibração inadequada. Uma ampla faixa de velocidades resulta no mesmo PWM.

Nessa região, um motor pode não vencer imediatamente o atrito estático enquanto o outro começa a girar. O uso de ceil() também cria degraus grandes e comportamento diferente entre avanço e ré.

### 3. Atualização sequencial e PWM não sincronizado

Os motores são atualizados sequencialmente:

    Motor_Run(MOTORA, ...)
    Motor_Run(MOTORB, ...)

Em KeyesDriver.c, são criados dois canais independentes:

    softPwmCreate(11, 0, 255)
    softPwmCreate(7, 0, 255)

Na implementação do WiringPi, o período é o intervalo básico de 100 microssegundos multiplicado pelo range. Com range igual a 255:

    período ≈ 255 × 100 µs ≈ 25,5 ms
    frequência ≈ 39,2 Hz

Como cada pino utiliza uma thread separada, os ciclos não são necessariamente sincronizados. Uma mudança pode atingir um motor quase um ciclo antes do outro.

Referência: <https://github.com/WiringPi/WiringPi/blob/master/wiringPi/softPwm.c>

### 4. Impacto possível do atraso inicial

Considerando velocidade de 0,25 m/s, atraso de 25 ms e separação entre rodas de 0,17 m:

    erro de orientação ≈ velocidade × atraso / separação
                       ≈ 0,25 × 0,025 / 0,17
                       ≈ 0,037 rad
                       ≈ 2,1°

Se depois ambas as rodas mantiverem velocidades iguais, o robô continuará com a nova orientação. Ao longo de cinco metros, um erro constante de 2,1 graus poderia representar teoricamente cerca de 18 cm de deslocamento lateral.

O atraso inicial é, portanto, uma hipótese plausível, embora sua origem mais provável seja a combinação de PWM por software, baixo ciclo de trabalho e diferenças físicas de partida.

### 5. Debounce compartilhado entre encoders

motor_encoder.c declara somente um instante de último pulso:

    const unsigned long intervaloDebounce = 40;
    volatile unsigned long ultimoPulso = 0;

A mesma variável é usada nas interrupções das duas rodas. Quando uma roda gera um pulso válido, os pulsos da outra ficam bloqueados durante 40 ms.

Isso limita as duas rodas juntas a menos de 25 pulsos por segundo. A 0,25 m/s, cada roda deveria produzir aproximadamente 15,4 pulsos/s, ou 30,8 pulsos/s no total. Portanto, o código necessariamente perde pulsos nessa velocidade.

O defeito compromete:

- velocidade medida de cada roda;
- odometria;
- estimativa de orientação;
- EKF;
- qualquer PID lateral que use /odom.

Também existe uma impressão de debug somente na interrupção esquerda. Operações de entrada e saída dentro de uma interrupção devem ser evitadas e introduzem outra assimetria.

### 6. Excesso de saída de debug

O projeto mantém USE_DEBUG igual a 1. Cada atualização imprime mensagens para os motores A e B. Com controle a 30 Hz, isso pode gerar mais de cem impressões por segundo, introduzir jitter e aumentar a diferença temporal entre a atualização do primeiro e do segundo motor.

### 7. A compensação existente não é usada no robô físico

O arquivo src/d_hospital_description/config/controllers.yaml contém multiplicadores de calibração. Entretanto, o lançamento físico carrega src/minihema_launch/config/controllers.yaml, que não contém esses multiplicadores.

Alterações feitas somente no YAML de d_hospital_description não afetam o robô iniciado por run_minihema.sh.

Também existem parâmetros geométricos divergentes:

| Configuração | Separação entre rodas | Raio da roda |
| --- | ---: | ---: |
| minihema_launch — robô físico | 0,170 m | 0,031 m |
| d_hospital_description | 0,165 m | 0,0325 m |

Esses valores devem ser medidos no robô e unificados.

## Diagnóstico consolidado

O desvio não deve ser atribuído apenas à ordem das duas chamadas Motor_Run().

A explicação mais provável é a combinação de:

1. PWM muito baixo e fortemente quantizado;
2. diferenças de atrito estático;
3. PWM por software em threads independentes;
4. ausência de controle individual de velocidade;
5. leitura incorreta dos encoders;
6. parâmetros físicos divergentes ou não calibrados.

O atraso percebido é relevante porque pode produzir um erro inicial de orientação, mas provavelmente é uma manifestação desses problemas, não uma causa isolada.

## Correções recomendadas

### 1. Corrigir os encoders

- Usar temporizadores de debounce separados para esquerda e direita.
- Remover impressões das interrupções.
- Definir o debounce em microssegundos.
- Calibrar o debounce usando os sinais reais.
- Proteger corretamente os contadores compartilhados.
- Confirmar se 12 pulsos por revolução corresponde ao sinal contado.

### 2. Implementar controle PI por roda

Controlar cada roda separadamente:

    erro = velocidade desejada - velocidade medida

    PWM = feedforward
        + Kp × erro
        + Ki × integral do erro

Um feedforward prático pode usar:

    PWM esquerdo = kS esquerdo + kV esquerdo × velocidade desejada
    PWM direito  = kS direito  + kV direito  × velocidade desejada

kS vence o atrito estático e kV representa a relação entre velocidade e PWM.

### 3. Calibrar o mapeamento de PWM

Levantar experimentalmente, para cada roda:

    PWM aplicado → velocidade real em rad/s

Depois, usar a relação inversa como feedforward. Pulsos por ciclo não devem ser tratados diretamente como porcentagem de PWM.

### 4. Melhorar a geração de PWM

Opções em ordem aproximada de robustez:

1. microcontrolador dedicado;
2. driver externo com canais sincronizados;
3. PWM de hardware da Raspberry Pi;
4. PWM por software com frequência e escala corrigidas.

Se softPwm for mantido, range igual a 100 elevaria a frequência nominal para aproximadamente 100 Hz e permitiria trabalhar diretamente em porcentagem. Isso ainda fica sujeito ao escalonamento do Linux.

### 5. Aplicar rampa de aceleração

Uma rampa reduz trancos:

    0% → PWM mínimo de partida → PWM nominal

Ela não garante partida simultânea, pois os motores podem ter limiares diferentes. O ideal é combiná-la com realimentação dos encoders.

### 6. Compensação temporária

Enquanto o controle individual não for implementado, pode-se adicionar ao arquivo realmente usado pelo robô:

    diff_controller:
      ros__parameters:
        wheel_separation_multiplier: 1.0
        left_wheel_radius_multiplier: 1.0
        right_wheel_radius_multiplier: 0.99

Se o robô puxa para a direita, isso geralmente indica que a roda direita percorre menos distância. Reduzir gradualmente o multiplicador direito faz o controlador solicitar maior velocidade angular para essa roda.

O ajuste deve ser realizado em passos de aproximadamente 1%, repetindo várias execuções. Esses parâmetros são destinados principalmente à calibração de diferenças de raio; ganhos próprios no driver são mais adequados para diferenças entre motores.

Documentação: <https://control.ros.org/rolling/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html>

### 7. Adicionar controle de rumo

Depois de corrigir os encoders, uma malha baseada na IMU pode remover erros residuais:

    erro_yaw = yaw_referencia - yaw_medido
    angular_z = Kp_yaw × erro_yaw

O PID lateral existente pode cumprir parte dessa função, mas atualmente depende de uma odometria afetada pelo erro dos encoders. Primeiro deve-se corrigir a camada de hardware.

## Protocolo experimental recomendado

### Medição elétrica e temporal

Com osciloscópio ou analisador lógico, registrar simultaneamente:

- PWM esquerdo;
- PWM direito;
- encoder esquerdo;
- encoder direito.

Medir o instante do comando, a primeira borda de PWM, o primeiro pulso dos encoders, a diferença entre o início físico das rodas e a frequência efetiva.

### Troca dos lados

- Se o desvio trocar de direção ao trocar os motores, a causa acompanha o motor ou redutor.
- Se permanecer no mesmo lado, investigar driver, GPIO, roda, chassi, caster e distribuição de carga.

### Ensaios para frente e para trás

Uma grande diferença entre os sentidos pode indicar assimetria mecânica, caster desalinhado, folga no redutor, problema de arredondamento ou diferença entre os circuitos de direção.

### Dados a registrar

- /cmd_vel;
- /joint_states;
- odometria bruta;
- yaw da IMU;
- odometria filtrada;
- referência externa da trajetória;
- tensão da bateria.

### Condições mecânicas

Documentar piso, carga, deformação das rodas, alinhamento dos eixos, liberdade do caster, tensão da bateria e temperatura dos motores e do driver.

## Critérios para localizar a causa

| Resultado | Interpretação provável |
| --- | --- |
| PWM começa em instantes diferentes | PWM, software ou GPIO |
| PWM começa junto, mas encoders não | motores, atrito ou carga |
| Encoders começam juntos, mas o robô desvia | rodas, alinhamento ou escorregamento |
| Desvio acompanha o motor após a troca | motor ou redutor |
| Desvio permanece no mesmo lado | driver, estrutura, roda ou carga |
| Odometria mostra desvio ausente na referência externa | encoder ou estimação |
| Referência externa mostra desvio ausente na odometria | encoder, raio ou calibração |

## Ordem sugerida de implementação

1. Remover o debug das interrupções e do ciclo normal dos motores.
2. Separar o debounce dos encoders e validar a contagem.
3. Medir a relação PWM versus velocidade de cada roda.
4. Corrigir o mapeamento de comando para PWM.
5. Implementar PI independente por roda.
6. Substituir ou melhorar a geração de PWM.
7. Medir e unificar raio e separação das rodas.
8. Aplicar trim temporário apenas se ainda necessário.
9. Adicionar controle de rumo por IMU.

## Limitações

Esta avaliação foi feita a partir do código e das configurações do repositório. Não foram medidos diretamente sinais GPIO, tensão nos motores, instante real de início das rodas, velocidade individual no protótipo, alinhamento mecânico, atrito do piso ou a versão exata do WiringPi instalada.

O código contém causas plausíveis e defeitos confirmados, mas a contribuição relativa de software, eletrônica e mecânica deve ser determinada pelos ensaios propostos.
