# Plano de ensaios dos motores e do desvio lateral

## Objetivo

Determinar se o desvio lateral do robô é causado principalmente por:

- diferença temporal no acionamento;
- geração de PWM por software;
- motores ou redutores;
- leitura incorreta dos encoders;
- configuração ou controle;
- características mecânicas do robô.

Os ensaios devem começar com o robô suspenso e terminar com trajetórias controladas no chão.

## 1. Sincronismo de partida dos motores

### Objetivo

Medir se os motores realmente recebem comando e começam a girar em instantes diferentes.

### Instrumentação

Com o robô suspenso, conectar um osciloscópio ou analisador lógico a:

- PWM esquerdo;
- PWM direito;
- encoder esquerdo;
- encoder direito.

### Procedimento

1. Manter o robô parado.
2. Aplicar um degrau de velocidade de 0 para 0,25 m/s.
3. Registrar os quatro sinais simultaneamente.
4. Repetir pelo menos 20 partidas.
5. Calcular:

       Δt_PWM = início do PWM direito − início do PWM esquerdo
       Δt_encoder = primeiro pulso direito − primeiro pulso esquerdo

### Interpretação

| Resultado | Indicação |
| --- | --- |
| PWM começa em instantes diferentes | Software, GPIO ou geração do PWM |
| PWM começa junto, mas os encoders não | Motor, redutor, atrito ou carga |
| Diferença varia muito entre repetições | Escalonamento do Linux ou limiar mecânico |
| O mesmo lado sempre começa primeiro | Assimetria sistemática |

Este é o ensaio mais direto para verificar a hipótese atual.

## 2. Limiar mínimo de partida

### Objetivo

Descobrir quanto PWM cada motor precisa para começar e continuar girando.

### Procedimento

Testar cada motor individualmente, aumentando lentamente o PWM:

    0%, 1%, 2%, 3% ... até o motor partir

Para cada motor e sentido, registrar:

- menor PWM que inicia o movimento;
- menor PWM que mantém o movimento;
- atraso até o primeiro pulso;
- velocidade estabilizada;
- tensão da bateria.

### Tabela sugerida

| Motor | Sentido | PWM de partida | PWM de manutenção | Atraso |
| --- | --- | ---: | ---: | ---: |
| Esquerdo | Frente |  |  |  |
| Direito | Frente |  |  |  |
| Esquerdo | Ré |  |  |  |
| Direito | Ré |  |  |  |

Se os limiares forem significativamente superiores aos comandos atuais de 1% ou 2%, o mapeamento presente no código está inadequado.

## 3. Validação dos encoders

### Objetivo

Confirmar o efeito do debounce compartilhado e verificar a precisão das contagens.

### Procedimento

Realizar três condições:

1. girar somente a roda esquerda;
2. girar somente a roda direita;
3. girar as duas simultaneamente na mesma velocidade.

Fazer um número conhecido de voltas. Para 20 voltas e 12 pulsos por revolução:

    contagem esperada = 20 × 12 = 240 pulsos

Repetir:

- com o código atual;
- depois de separar os temporizadores de debounce;
- com as mensagens de debug removidas das interrupções.

### Interpretação

Se cada encoder contar corretamente sozinho, mas perder pulsos quando ambos giram, o problema do debounce compartilhado estará confirmado experimentalmente.

## 4. Curva PWM versus velocidade

### Objetivo

Construir o mapeamento real de cada motor.

### Procedimento

Com o robô suspenso, testar:

    PWM: 10%, 15%, 20%, 25%, 30%, 40%, 50%, 60%, 80%

Para cada ponto:

1. aplicar o PWM;
2. aguardar aproximadamente dois segundos;
3. calcular a velocidade média pelo encoder;
4. repetir pelo menos cinco vezes;
5. testar para frente e para trás.

### Resultados esperados

Construir uma curva para cada roda:

    PWM aplicado → velocidade real em rad/s

Essas curvas permitem identificar:

- zona morta;
- PWM mínimo de partida;
- ganho de cada motor;
- diferença entre os lados;
- região aproximadamente linear;
- saturação.

Os resultados devem substituir o coeficiente arbitrário 1.65 usado atualmente.

## 5. Troca cruzada dos motores

### Objetivo

Descobrir se o problema acompanha o motor ou permanece no mesmo lado do robô.

### Procedimento

1. Executar uma trajetória de referência.
2. Trocar as conexões dos motores entre os canais A e B.
3. Repetir a trajetória.
4. Se necessário, trocar fisicamente os conjuntos motor e redutor entre os lados.
5. Garantir que a lógica de direção permaneça correta após a troca.

### Interpretação

| Comportamento | Causa mais provável |
| --- | --- |
| O desvio troca de lado | Motor ou redutor |
| O desvio permanece no mesmo lado | Driver, roda, chassi, caster ou carga |
| Muda ao trocar canais, mas não os motores | Canal do driver ou GPIO |
| Muda ao trocar fisicamente os motores | Conjunto motor e redutor |

## 6. Trajetória reta em malha aberta

### Objetivo

Quantificar o desvio sem PID lateral ou EKF mascarando o comportamento.

### Comando

    linear.x = velocidade constante
    angular.z = 0

### Condições sugeridas

| Sentido | Velocidades |
| --- | --- |
| Frente | 0,10; 0,20; 0,25 m/s |
| Ré | −0,10; −0,20; −0,25 m/s |

Realizar pelo menos dez repetições por condição, percorrendo entre três e cinco metros.

### Métricas

- atraso relativo de partida;
- yaw após 0,25 m e 0,50 m;
- desvio lateral em 1 m, 3 m e 5 m;
- yaw final;
- velocidade de cada roda;
- tensão da bateria;
- lado do desvio.

## 7. Partida versus regime permanente

### Objetivo

Verificar se o desvio nasce somente na partida ou continua crescendo.

Separar as métricas em:

    erro inicial  = yaw e deslocamento nos primeiros 0,50 m
    erro de regime = inclinação da trajetória depois de 0,50 m

### Interpretação

- Erro grande no início e trajetória depois paralela: problema de partida.
- Curvatura contínua: velocidades permanentes diferentes.
- Trajetória inicialmente reta e depois instável: bateria, aquecimento, encoder ou controle.
- Desvio irregular: piso, escorregamento ou jitter.

## 8. Comparação das formas de gerar PWM

### Objetivo

Determinar a contribuição específica do softPwm.

### Configurações

1. implementação atual, com range igual a 255;
2. softPwm com range igual a 100;
3. PWM de hardware ou microcontrolador, se disponível.

Manter o mesmo ciclo de trabalho efetivo e comparar:

- diferença entre as primeiras bordas;
- diferença entre os primeiros pulsos;
- desvio lateral;
- variabilidade entre partidas.

Se o atraso diminuir com PWM sincronizado, a geração por software tem contribuição relevante.

## 9. Rampa e pulso de partida

Comparar:

1. degrau direto para o PWM nominal;
2. rampa gradual;
3. pulso de partida seguido do PWM nominal.

Exemplo:

    25% por 100 ms → PWM nominal

A melhor configuração deve:

- iniciar ambas as rodas consistentemente;
- minimizar a diferença entre os primeiros pulsos;
- evitar salto ou patinagem;
- apresentar baixa variabilidade.

## 10. Comparação das correções de software

Avaliar as versões na seguinte ordem:

| Versão | Alteração |
| --- | --- |
| A | Código atual |
| B | Debug desativado |
| C | Debounce separado |
| D | Mapeamento PWM calibrado |
| E | PI independente por roda |
| F | PI por roda e controle de rumo |

Usar exatamente o mesmo protocolo e as mesmas métricas. Isso permite atribuir a melhora a uma alteração específica.

## 11. Ensaio de compensação simples

Antes de implementar o PI, pode-se avaliar um trim provisório.

Se o robô puxa para a direita, testar ganhos direitos:

    1,00
    1,01
    1,02
    1,03
    1,04

Alternativamente, no diff_drive_controller, testar multiplicadores de raio direitos:

    1,00
    0,99
    0,98
    0,97
    0,96

Usar parte das execuções para escolher o valor e execuções novas para validá-lo. O mesmo conjunto de dados não deve ser usado simultaneamente para sintonia e avaliação.

## 12. Influência mecânica e elétrica

Repetir uma condição de referência variando somente um fator:

- bateria cheia e parcialmente descarregada;
- piso liso e áspero;
- robô sem carga e com carga;
- caster em orientações iniciais diferentes;
- rodas reapertadas e alinhadas;
- motores frios e aquecidos.

Também empurrar manualmente o robô sem alimentação para observar:

- resistência diferente entre os lados;
- roda raspando;
- rolamento apertado;
- caster direcionando o robô;
- desalinhamento dos eixos.

## Referência externa

Não usar apenas a odometria do robô, pois os encoders podem perder pulsos. Utilizar, quando possível:

- câmera superior calibrada com marcador ArUco;
- sistema de captura de movimento;
- linha física e medições em pontos fixos;
- IMU calibrada para medir yaw.

Registrar simultaneamente:

- /cmd_vel;
- /joint_states;
- odometria bruta;
- /odometry/filtered;
- IMU;
- referência externa;
- tensão da bateria.

## Padronização dos ensaios

Para melhorar a confiabilidade:

- usar pelo menos dez repetições nas trajetórias e vinte nas partidas;
- alternar ou aleatorizar a ordem das condições;
- manter a mesma posição inicial;
- documentar piso, carga e bateria;
- aquecer ou resfriar os motores de maneira consistente;
- separar os dados de sintonia dos dados de validação;
- guardar versão do código e parâmetros de cada execução.

## Conjunto mínimo recomendado

Se houver pouco tempo, priorizar:

1. sincronismo dos dois PWMs e primeiros pulsos;
2. limiar de partida individual;
3. validação simultânea dos encoders;
4. troca cruzada dos motores e canais;
5. dez trajetórias com o código atual;
6. dez trajetórias após corrigir debounce, debug e mapeamento do PWM.

Esses ensaios devem indicar se o desvio nasce no software, no acionamento elétrico, nos motores ou na mecânica.
