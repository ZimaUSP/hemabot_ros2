# Recomendações para a continuidade da pesquisa e publicação no IEEE

## Objetivo e alcance da avaliação

Transformar a iniciação científica descrita em [relatorio_final.pdf](relatorio_final.pdf) em um artigo sobre precisão e confiabilidade do movimento do Mini-Hema, plataforma do projeto HemaBot.

Esta avaliação foi elaborada a partir da leitura do relatório, dos scripts e das configurações do repositório e da inspeção dos tópicos de bags disponíveis. As métricas do relatório ainda não foram reproduzidas independentemente, e a simulação não foi executada para validar as hipóteses abaixo. Os arquivos atuais podem diferir das versões usadas nos experimentos históricos.

**Recomendação principal:** realizar uma nova etapa de validação antes da submissão, separando o efeito do controlador, do estimador de estado e do protocolo experimental.

## 1. Pontos fortes da pesquisa

- Pergunta de pesquisa delimitada: avaliar a redução dos erros lateral e longitudinal em uma trajetória retilínea simulada.
- Comparação entre malha aberta, controlador isolado e configuração denominada PID+EKF.
- Repetições experimentais e apresentação de métricas quantitativas.
- Uso de *ground truth* para avaliar o movimento real na simulação, em vez de depender exclusivamente da odometria usada na realimentação.
- Reconhecimento de que, com `Ki = 0`, o controlador opera como PD com termo adicional de orientação.
- Discussão explícita das limitações da simulação e das execuções com erros elevados.

## 2. Resultado que pode orientar a continuação

Os valores abaixo são os **informados no relatório**, não uma nova análise dos bags.

| Configuração | RMSE lateral | RMSE longitudinal |
| --- | ---: | ---: |
| Malha aberta | 5,3 mm | 0,4615 m |
| PD com termo de orientação | 5,8 mm | 0,0299 m |
| Configuração denominada PD+EKF | 4,0 mm | 0,8316 m |

Não há uma configuração superior em todas as métricas. A configuração denominada PD+EKF tem menor RMSE lateral, mas apresenta grande erro longitudinal em algumas execuções. O PD isolado reduz o MAE lateral, porém seu RMSE lateral é ligeiramente maior que o da malha aberta.

Uma pergunta para a próxima etapa é:

> Em quais condições a fusão sensorial melhora a precisão do rastreamento e em quais condições prejudica a conclusão confiável do movimento?

As diferenças observadas ainda precisam de análise de incerteza e de uma comparação que controle os demais fatores experimentais.

## 3. Questões a resolver antes de novas conclusões

### 3.1 Confirmar o caminho da realimentação do EKF

A seção 5.3.3 do relatório reconhece que não foi possível confirmar se o controlador recebeu efetivamente a estimativa filtrada. Nos launches atuais, a saída `/odometry/filtered` é remapeada para `/odom`, enquanto a configuração do EKF indica `odom` como entrada. Isso exige verificar os tópicos resolvidos e seus publicadores para evitar realimentação da própria saída e mistura de fontes. Na simulação, o plugin também publica odometria e TF.

**Ações:**

- Definir tópicos distintos para odometria bruta e filtrada, por exemplo `/odom/raw` e `/odometry/filtered`.
- Configurar explicitamente o tópico de entrada do controlador em cada cenário.
- Registrar os publicadores de cada tópico, os parâmetros efetivos dos nós e os responsáveis pelas transformações TF.
- Verificar se o YAML do EKF é aplicado ao nome real do nó e se `use_sim_time` é coerente em todos os componentes.
- Confirmar a origem e o significado da odometria produzida pelo plugin de simulação; não presumir que ela representa encoders ruidosos.

**Critério de conclusão:** demonstrar, com configuração e registros de execução, qual fonte alimenta o controlador e quais medições alimentam o EKF.

### 3.2 Separar correção lateral de precisão da parada

O script atual de malha aberta usa `timeout` para movimentar o robô por um tempo definido. O controlador encerra ao atingir uma distância medida pela odometria. Sua velocidade linear é constante, e a correção PD atua na velocidade angular.

Portanto, a melhora longitudinal pode decorrer principalmente da parada por distância, além de qualquer efeito da correção de trajetória. Essa é uma hipótese a testar, não uma causa já demonstrada.

**Ações:**

- Usar o mesmo critério de término ao comparar controladores laterais.
- Avaliar separadamente a influência de término por tempo e término por distância.
- Usar tempo de simulação para o protocolo; tratar um timeout em tempo de parede apenas como proteção operacional, registrando quando ele ocorrer.
- Documentar aceleração, desaceleração, duração efetiva do movimento e instante de avaliação da pose final.
- Manter o *ground truth* como referência de avaliação, sem introduzi-lo inadvertidamente na realimentação de um método que se pretende avaliar com sensores.

**Critério de conclusão:** distinguir quantitativamente os efeitos da correção lateral, da estimação e da política de parada.

### 3.3 Vincular resultados aos dados e parâmetros históricos

Foram encontradas diferenças entre o relatório e os arquivos atuais:

| Item | Evidência observada | Ação necessária |
| --- | --- | --- |
| Ganhos | O relatório informa `Kp = 8` e `Kd = 4`; o script atual usa `Kp = 0,8`, `Kd = 0,15` e `Kh = 0,6`. | Identificar a configuração usada em cada conjunto histórico. |
| Repetições | A pasta de malha aberta contém 50 bags, mas o resumo declara 30. | Contar execuções disponíveis, analisadas, válidas e malsucedidas e corrigir os metadados. |
| Tópico de referência | O relatório menciona `/gazebo/ground_truth/state`; os bags inspecionados registram `/ground_truth/state`. | Uniformizar documentação e leitor de dados. |
| Frequências | O relatório menciona aquisição a 100 Hz; o plugin de *ground truth* atual está configurado a 50 Hz. | Documentar configuração histórica e medir frequência efetiva por tópico e execução. |
| Análise | Os scripts atuais têm pressupostos e entradas que não correspondem integralmente aos três cenários do relatório. | Identificar ou reconstruir o pipeline que gerou as tabelas e figuras finais. |

Essas diferenças não comprovam que os resultados estejam incorretos; impedem, porém, sua reprodução direta com a configuração atual.

**Critério de conclusão:** uma tabela rastreável relacionando cenário, execução, bag, configuração, versão do código e resultado.

### 3.4 Investigar as execuções com erros elevados

Os erros longitudinais próximos de −3 m e −5 m podem representar movimento incompleto, timeout, perda de odometria, reset inadequado ou problemas de estimação. O erro final não permite identificar a causa sozinho.

**Ações:**

- Examinar séries temporais de pose real, odometria bruta e filtrada e comandos de velocidade.
- Registrar motivo de término, estado do controlador, interrupções das medições e saltos na estimativa.
- Conferir o reset do mundo, do estimador e da referência do controlador entre execuções.
- Manter todas as execuções na análise principal e relatar a taxa de falhas.
- Apresentar, como análise complementar, o desempenho das execuções concluídas e das falhas diagnosticadas.

O corte exploratório de 18 cm não deve se tornar critério de exclusão apenas por reduzir o RMSE. Exclusões por falha de aquisição precisam de justificativa verificável e critérios definidos antes dos novos testes. Falhas do sistema são parte do resultado de confiabilidade.

## 4. Melhorias técnicas para sustentar os experimentos

### Referencial da trajetória

O controlador atual calcula o erro lateral por `y_ref - current_y` e a distância por `abs(current_x - x0)`. Isso pressupõe uma reta alinhada ao eixo X global, embora o código capture uma orientação inicial.

Usar deslocamentos relativos à pose inicial e projetá-los no referencial da reta:

```text
Δx = x - x₀
Δy = y - y₀

desvio lateral = -sen(θ₀) · Δx + cos(θ₀) · Δy
avanço na reta =  cos(θ₀) · Δx + sen(θ₀) · Δy
```

Definir consistentemente o sinal da correção e o avanço desejado, inclusive para movimento de ré. Para erro longitudinal final, explicitar a diferença entre o avanço medido e o avanço alvo; a projeção sozinha representa deslocamento, não necessariamente erro.

### Atualização e disponibilidade das medições

- Parar o movimento quando a odometria estiver vencida.
- Atualizar o termo derivativo com novas medições e intervalos temporais coerentes; avaliar filtragem para evitar amplificação de ruído.
- Validar parâmetros, limites e comportamento após resets ou saltos no relógio da simulação.
- Registrar frequência efetiva, atraso e saturação dos comandos.

### Partida, parada e calibração

- Introduzir e avaliar rampas de aceleração e desaceleração para reduzir trancos e ultrapassagem do alvo.
- Verificar raio efetivo das rodas, separação entre rodas, encoders e assimetrias dos atuadores.
- Separar o efeito da calibração mecânica/cinemática do efeito do controlador.
- Padronizar os parâmetros efetivos usados pelos scripts, YAML e código.

O controlador diferencial oferece parâmetros de calibração, limites de movimento e timeout de comandos. Verificar sua aplicabilidade à versão e à arquitetura efetivamente usadas: [documentação oficial para ROS 2 Humble](https://control.ros.org/humble/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html).

## 5. Plano de continuidade

| Etapa | Trabalho | Entrega e critério de avanço |
| --- | --- | --- |
| 1. Auditoria dos resultados existentes | Identificar os três conjuntos experimentais, reconstruir parâmetros e recalcular métricas com *ground truth*. | Tabelas e figuras reproduzíveis; diferenças em relação ao relatório explicadas. |
| 2. Comparação controlada | Comparar PD com odometria bruta e PD com EKF, mantendo ganhos, limites, referência e término iguais. Separar os tópicos brutos e filtrados. | Evidência do efeito específico do estimador. |
| 3. Robustez e diagnóstico | Variar velocidade, sentido, orientação inicial, ruído e assimetria das rodas. Registrar motivo de término e idade das medições. | Condições de sucesso, causas de falha e limites do método. |
| 4. Comparador adicional | Incluir um controlador adequado a robôs diferenciais, com esforço de sintonia equivalente. | Comparação além da malha aberta, com escolha justificada pela literatura. |
| 5. Validação física | Repetir um subconjunto no Mini-Hema com medição externa e incerteza conhecida. | Evidência de transferência da simulação para o protótipo. |
| 6. Manuscrito e artefatos | Consolidar contribuição, figuras, limitações, código e dados. | Artigo e materiais suplementares prontos para revisão com o orientador. |

Começar por um conjunto pequeno de condições para depurar o protocolo. A quantidade de repetições dos testes finais deve ser justificada pela variabilidade e pela precisão estatística desejada, em vez de adotar 50 automaticamente. Separar condições usadas na sintonia das usadas na avaliação final.

## 6. Métricas e análise estatística

Definir previamente o que significa movimento preciso: tolerâncias de desvio lateral, orientação e parada, além de limites de suavidade e taxa de conclusão. Justificar essas tolerâncias por requisitos da plataforma e da aplicação.

| Aspecto | Indicadores recomendados |
| --- | --- |
| Rastreamento lateral | MAE e RMSE ao longo do percurso, desvio máximo, erro final e integral do erro absoluto. |
| Orientação | Erro angular ao longo do percurso e ao final. |
| Parada | Erro longitudinal final, ultrapassagem do alvo e distância após comando de parada. |
| Estimação | Erro da odometria bruta e filtrada em relação ao *ground truth*, após alinhamento de referenciais e sincronização temporal. |
| Movimento | Tempo de conclusão, variação dos comandos, aceleração e tempo em saturação. |
| Confiabilidade | Taxa de conclusão, taxa de violação das tolerâncias, motivos e condições das falhas. |

MAE e RMSE dos erros finais podem esconder desvios grandes durante o percurso que desaparecem antes da parada. Distinguir métricas calculadas ao longo de uma trajetória das calculadas sobre os erros finais de várias execuções.

**Cuidados estatísticos:**

- Calcular intervalos de confiança usando a execução como unidade experimental; mensagens do mesmo bag não são repetições independentes.
- Documentar sementes aleatórias, condições iniciais e procedimentos de reset. Reiniciar o mundo não demonstra, por si só, independência entre ensaios.
- Randomizar ou alternar a ordem dos métodos para reduzir efeitos de degradação da simulação e ordem de execução.
- Quando apropriado, comparar métodos em condições e sementes correspondentes, preservando esse pareamento na análise.
- Apresentar distribuições, magnitude das diferenças e incerteza, além das médias.
- Evitar declarar superioridade ou significância estatística somente com base em diferenças entre valores pontuais.

## 7. Validação no protótipo

Uma validação física fortaleceria a contribuição prática. Não é necessário iniciar em ambiente hospitalar: um espaço de laboratório com condições documentadas permite avaliar transferência sem extrapolar o escopo.

**Protocolo inicial sugerido:**

- Ensaios retilíneos para frente e de ré, incluindo orientações iniciais diferentes.
- Variação controlada de velocidade e carga transportada.
- Avaliação em condições de piso documentadas.
- Medição externa da trajetória, por exemplo por câmera calibrada e marcadores ou sistema de captura de movimento.
- Quantificação da incerteza da referência externa. Para investigar diferenças de poucos milímetros, a referência deve ter precisão suficiente para distingui-las.
- Comparação entre resultados físicos e simulados, discutindo diferenças de atrito, folgas, sensores e atuadores.

Os resultados não devem ser apresentados como validação de navegação hospitalar completa se o experimento avaliar somente rastreamento retilíneo em laboratório.

## 8. Contribuição científica proposta

Evitar limitar a contribuição à aplicação de técnicas conhecidas de PID e EKF ao HemaBot. Uma direção mais forte é:

> Um estudo reproduzível sobre a influência da estimação de estado na precisão e na confiabilidade do rastreamento de um robô diferencial para logística hospitalar, incluindo diagnóstico de falhas e validação no protótipo.

Essa é uma proposta de recorte, cuja novidade ainda precisa ser demonstrada por revisão bibliográfica. Um controlador adicional ajuda a contextualizar desempenho, mas não estabelece novidade sozinho.

**Revisão bibliográfica a aprofundar:**

- Rastreamento de trajetórias em robôs diferenciais.
- Fusão de odometria e IMU e interação entre estimador e controlador.
- Calibração de erros sistemáticos de odometria, incluindo UMBmark.
- Robustez a ruído, atraso, perda de medições e assimetria dos atuadores.
- Avaliação e requisitos de robôs destinados à logística hospitalar.

Organizar uma tabela de trabalhos relacionados com plataforma, método, comparadores, condições experimentais, métricas e limitações. Priorizar artigos e documentação original para fundamentar as decisões. Cursos podem ser reconhecidos como apoio de implementação, mas não substituem referências científicas para sustentar a contribuição.

## 9. Estratégia de publicação no IEEE

O IEEE reúne conferências e periódicos com escopos e exigências diferentes. Escolher o veículo junto ao orientador depois de delimitar a contribuição e o nível de validação disponível.

| Possibilidade | Avaliação para este projeto |
| --- | --- |
| Conferência compatível com robótica móvel, controle ou sistemas aplicados | Direção inicial recomendada para um estudo experimental delimitado, depois de resolver a rastreabilidade e a comparação entre métodos. Conferir escopo e chamada vigente. |
| IEEE Robotics and Automation Letters (RA-L) | Exige fortalecer a diferenciação científica; seu escopo enfatiza ideias e resultados inovadores. Não presumir que a aplicação de PD e EKF, isoladamente, seja suficiente. |
| IEEE Robotics and Automation Practice (RA-P) | Pode ser considerada com contribuição prática replicável e demonstração física; seu escopo exige resultados demonstrados ou implantados em situações reais. |

Fontes oficiais consultadas:

- [Escopo da RA-L](https://www.ieee-ras.org/publications/ieee-robotics-and-automation-letters/).
- [Informações para autores da RA-L](https://www.ieee-ras.org/publications/ra-l/ra-l-information-for-authors/).
- [Escopo da RA-P](https://www.ieee-ras.org/publications/ra-p/).
- [Orientações do IEEE para estruturar artigos de conferência](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/structure-your-paper/).

As recomendações de adequação acima são avaliações deste projeto, não garantia de aceitação. Verificar as regras vigentes do veículo escolhido antes de definir formato, extensão e calendário.

## 10. Reprodutibilidade e estrutura do artigo

Para cada execução, salvar configuração efetiva, versão do código, versões de ROS/Gazebo, mundo e modelo utilizados, sementes, tópicos, frequências observadas, logs e motivo de término. Preservar os dados históricos sem sobrescrevê-los.

Preparar um comando ou procedimento documentado que gere as tabelas e figuras a partir dos dados. Separar dados brutos, resultados derivados e configurações. Disponibilizar código e dados com licença apropriada quando autorizados pelos responsáveis pelo projeto, preferencialmente em uma versão arquivada e identificável.

O IEEE incentiva metodologia detalhada e compartilhamento de dados e código para permitir verificação e reprodução: [orientações de reprodutibilidade](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/research-reproducibility/).

**Estrutura sugerida para o manuscrito:**

1. Introdução: problema, lacuna e contribuição delimitada.
2. Trabalhos relacionados: comparação com pesquisas próximas.
3. Sistema e métodos: plataforma, arquitetura de tópicos, controle e estimação.
4. Protocolo experimental: condições, sintonia, referências de avaliação e análise estatística.
5. Resultados: precisão, confiabilidade, robustez e validação física, conforme o escopo realizado.
6. Discussão: causas das falhas, limites e transferência entre simulação e protótipo.
7. Conclusão: respostas sustentadas pelos experimentos e questões restantes.

## 11. Primeira ação recomendada

**Auditar os três cenários e executar uma comparação que separe o efeito do EKF do efeito da parada por distância.** Essa etapa determina quais conclusões atuais se sustentam e fornece a base para escolher a contribuição central do artigo.
