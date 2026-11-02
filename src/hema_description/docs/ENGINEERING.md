# Hema V4 — memória de engenharia da descrição Xacro

Esta descrição representa a montagem exportada em `Hema_V4/HEMA.stl/`: **227 peças, 15 elos físicos e o referencial virtual `tool0`**. A massa estimada é **22,764686 kg**, com os fatores de escala de massa em 1. A geometria foi medida; materiais, propriedades de atuação e parte da cinemática são hipóteses identificadas neste documento. O modelo não constitui uma identificação dinâmica do robô real.

## Fonte e seleção da montagem

Arquivo de origem: `Hema_V4 (1).zip`.

SHA-256: `e5117d457cbf26679bcbcf77052c3f51f84f6fc7c28a5b13a154e61587ee3ce8`.

O inventário contém 296 arquivos: 246 STL, 28 SLDPRT, 13 SLDASM, uma imagem PNG e oito arquivos auxiliares. A análise usa exclusivamente os 227 STL de `HEMA.stl`, que já compartilham o referencial da montagem. Nomes contendo `.STEP` dentro do nome de um STL não correspondem a arquivos STEP independentes no ZIP.

Os outros 19 STL, na pasta de cortes da carenagem para impressão, foram excluídos: representam cortes ou variantes da mesma carenagem e sua inclusão duplicaria a massa e a aparência. Os arquivos nativos SolidWorks, inclusive versões anteriores e componentes avulsos, também não foram somados à montagem STL. Não foi feita leitura de materiais, mates, limites de juntas ou propriedades físicas dos arquivos nativos. A atribuição de peças a elos usa nomes e posições geométricas. Não há deduplicação cega de instâncias idênticas: parafusos e perfis repetidos em posições diferentes continuam contados como peças distintas.

`archive_inventory.json` registra o que entrou no cálculo; `cad_parts.json` e `cad_parts.csv` registram material presumido, densidade, método de volume, massa, CoM, tensor e origem de cada peça. `scripts/analyze_cad.py` reproduz essa análise sem executar arquivos do ZIP. Os nomes com caracteres corrompidos refletem a codificação dos nomes no arquivo de origem.

## Escala, coordenadas e origens

Os STL de origem foram interpretados em milímetros pela escala dos componentes e da montagem. Os STL entregues em `meshes/` estão em metros; o Xacro usa `scale="1 1 1"`. Aplicar outra escala de 0,001 às malhas entregues produziria um erro de escala.

Para um ponto CAD `p_CAD` em mm, a transformação para `base_link` em m é:

```text
p_base = 0.001 R (p_CAD - o_CAD)

o_CAD = [1177.6824798583984,
         1410.248779296875,
         2214.512939453125] mm

R = [ 0  0 -1
     -1  0  0
      0  1  0 ]
```

O sistema resultante tem +X para a frente, identificada pelo lado dos sensores ultrassônicos; +Y para a esquerda; +Z para cima. `base_link` fica no ponto médio do eixo das rodas motrizes. Não existe junta fixa com o mundo: a base participa da dinâmica livre do simulador.

Em `config/cad_parameters.yaml`, `origin` é a origem do elo expressa em `base_link` na pose CAD original. `com` é o centro de massa em coordenadas locais do próprio elo. `joint_origin`, quando presente, é a translação em relação ao elo pai. Os referenciais locais mantêm a orientação do sistema ROS; as malhas já receberam a rotação `R` e a translação para seu elo. A origem visual é, portanto, zero.

| Referencial ou grandeza | Posição/dimensão medida, em m |
| --- | --- |
| Eixo da roda esquerda em `base_link` | `(0, +0.2047557526, 0)` |
| Eixo da roda direita em `base_link` | `(0, -0.2047556915, 0)` |
| Raio de contato das rodas motrizes | `0.0793708496094` |
| Largura de contato da banda da roda | `0.0359817810059` |
| Distância entre planos médios das rodas | `0.409511444092` |
| Raio/largura das rodas dos rodízios | `0.025 / 0.0228` |
| Pivôs dianteiros dos rodízios, pose CAD | `x=0.1839000244`, `y=+0.1551500397/-0.1548499908`, `z=-0.018` |
| Pivôs traseiros dos rodízios, pose CAD | `x=-0.1835999756`, mesmos `y` e `z` |
| Eixo da roda em relação ao garfo do rodízio | aproximadamente `(0.01985998535, 0, -0.03074719238)` |
| Corrediça intermediária esquerda/direita em `base_link` | `(0.01539996338, +0.1381951447/-0.1368049469, 0.1913499146)` |
| Corrediça interna esquerda/direita em `base_link` | `(0.01539996338, +0.1374999847/-0.1375000153, 0.1945993652)` |
| `tool0` em relação a `slide_left_inner_link` | `(0.249, 0, 0)` |

A largura de contato de `0.03598178 m` foi medida apenas na banda externa da roda. A extensão de aproximadamente `0.111 m` da malha completa inclui o eixo; usá-la como largura de colisão do pneu criaria contatos inexistentes. O conjunto motor/eixo/pneu não veio separado em sólidos funcionais móveis: a malha e a inércia do conjunto foram atribuídas à roda, uma aproximação que também faz a geometria do eixo acompanhar sua rotação.

Na pose CAD, o ponto inferior das rodas dos rodízios é `z=-0.07374719238 m`; o das rodas motrizes é `z=-0.07937084961 m`. O parâmetro `caster_z_adjust` desloca os quatro conjuntos de rodízios em **-0.00562365722656 m**, igualando as alturas de contato em piso plano. Trata-se de ajuste de simulação, não de dimensão extraída da montagem. Definir `caster_z_adjust:=0` restaura a posição CAD. A mudança atua na junta de giro do garfo e, por descendência, na roda; o CoM local e o tensor de cada elo permanecem os mesmos. Os valores `origin` do YAML preservam a pose CAD sem esse ajuste.

## Volume, materiais e massa

Para cada peça foi usado `m = ρ V`. **Não há metadados de material verificados** nos STL analisados; os nomes de materiais abaixo são hipóteses revisáveis, e as densidades são valores de modelagem adotados. As cores de `materials.xacro` não definem densidade ou atrito.

| Material presumido | Densidade adotada (kg/m³) | Critério de atribuição | Peças | Massa subtotal (kg) |
| --- | ---: | --- | ---: | ---: |
| Alumínio, referência 6061 | 2700 | Perfis, cantoneiras e suportes do motor | 44 | 5.731946 |
| Aço | 7850 | Corrediças, fixadores, garfos/eixos e suportes dos rodízios | 159 | 4.564083 |
| PLA | 1240 | Carenagem e acabamento do lidar | 2 | 6.497377 |
| ABS | 1040 | Componentes plásticos restantes; hipótese de classificação | 12 | 0.095217 |
| Nylon | 1150 | Quatro rodas dos rodízios | 4 | 0.110367 |
| Eletrônica, composto efetivo | 1800 | Quatro módulos ultrassônicos representados | 4 | 0.025095 |
| Motor/roda, composto efetivo | 3000 | Duas malhas completas `Hoverboardwheel` | 2 | 5.740601 |
| **Total** | — | — | **227** | **22.764686** |

A densidade efetiva de `3000 kg/m³` do conjunto motor/roda aproxima uma combinação desconhecida de metal, polímero e vazios. Não é a densidade do pneu nem um dado do fabricante, e constitui uma fonte importante de incerteza. A aparência `hema_rubber` dessas malhas é apenas visual. A constante de borracha `1100 kg/m³` existe no analisador, mas nenhuma peça foi classificada isoladamente como borracha neste conjunto de dados.

A carenagem PLA usa o volume sólido delimitado pela malha, preservando as cavidades que ela representa. Não foi aplicado percentual arbitrário de preenchimento de impressão. Paredes, infill e material reais devem ser conferidos antes de interpretar a estimativa de 6,497377 kg dos dois componentes como uma massa fabricada. Para revisar materiais por peça, alterar a classificação/densidades e repetir a análise; os fatores Xacro de massa são ajustes uniformes por grupo e não substituem uma distribuição de densidade diferente entre peças.

| Método de obtenção de volume | Peças | Volume subtotal (m³) | Fração do volume | Massa subtotal (kg) |
| --- | ---: | ---: | ---: | ---: |
| STL originalmente fechado (`closed_stl`) | 217 | 0.008098014514959 | 80.503751% | 16.970906 |
| Rodas fechadas após reparar pequenos furos | 2 | 0.001913533669928 | 19.022766% | 5.740601 |
| Envoltória convexa de STL aberto | 8 | 0.000047628462102 | 0.473483% | 0.053179 |
| **Total** | **227** | **0.010059176646989** | **100%** | **22.764686** |

Os oito proxies convexos pertencem ao botão de emergência: quatro componentes `M3F`, dois `Miros switch`, um `ill_stecker` e um `plastic stick`. Somam **0,233602% da massa estimada**. A envoltória convexa pode preencher concavidades ou espaços vazios e não equivale a volume CAD exato. Nas duas rodas foram preenchidos apenas pequenos furos triangulares/quadrangulares aceitos pelo reparador; a superfície visual original foi preservada. A soma de volumes é uma soma de peças, não uma união booleana que desconta interpenetrações de montagem.

O ZIP contém arquivos nativos com nomes de Jetson Nano, Raspberry e RPLidar, mas eles não aparecem como corpos identificáveis usados na exportação `HEMA.stl`. Não foi inventada massa para essas placas ou para um lidar completo a partir desses nomes. O acabamento do lidar foi contado como peça estrutural PLA. Também não foi identificada bateria na montagem STL. Carga útil, bateria, cabeamento adicional e eletrônica ausente exigem inclusão explícita de geometria, massa e CoM; a massa total documentada corresponde somente às 227 peças analisadas.

## Elos e cadeia cinemática

Os nomes da tabela são os nomes reais emitidos pelo Xacro. As massas são anteriores a qualquer `mass_scale`, `base_mass_scale`, `drive_mass_scale`, `caster_mass_scale` ou `slide_mass_scale`. `continuous` significa rotação sem batentes de posição; limites de torque e velocidade continuam definidos. As quatro corrediças são `fixed` por padrão e tornam-se `prismatic` passivas somente com `articulate_slides:=true`.

| Nome do elo | Massa (kg) | Material assumido | Junta associada: tipo | Eixo local | Limites de posição (m ou rad) |
| --- | ---: | --- | --- | --- | --- |
| `base_link` | 16.184621 | Alumínio + aço + PLA + ABS + eletrônica | raiz livre | — | — |
| `left_wheel_link` | 2.870300 | Motor/roda composto | `left_wheel_joint`: continuous, atuada | `(0,1,0)` | sem batentes, rad |
| `right_wheel_link` | 2.870301 | Motor/roda composto | `right_wheel_joint`: continuous, atuada | `(0,1,0)` | sem batentes, rad |
| `caster_front_left_fork_link` | 0.027634 | Aço | `caster_front_left_swivel_joint`: continuous, passiva | `(0,0,1)` | sem batentes, rad |
| `caster_front_left_wheel_link` | 0.027592 | Nylon | `caster_front_left_wheel_joint`: continuous, passiva | `(0,1,0)` | sem batentes, rad |
| `caster_front_right_fork_link` | 0.027633 | Aço | `caster_front_right_swivel_joint`: continuous, passiva | `(0,0,1)` | sem batentes, rad |
| `caster_front_right_wheel_link` | 0.027592 | Nylon | `caster_front_right_wheel_joint`: continuous, passiva | `(0,1,0)` | sem batentes, rad |
| `caster_rear_left_fork_link` | 0.027634 | Aço | `caster_rear_left_swivel_joint`: continuous, passiva | `(0,0,1)` | sem batentes, rad |
| `caster_rear_left_wheel_link` | 0.027592 | Nylon | `caster_rear_left_wheel_joint`: continuous, passiva | `(0,1,0)` | sem batentes, rad |
| `caster_rear_right_fork_link` | 0.027633 | Aço | `caster_rear_right_swivel_joint`: continuous, passiva | `(0,0,1)` | sem batentes, rad |
| `caster_rear_right_wheel_link` | 0.027592 | Nylon | `caster_rear_right_wheel_joint`: continuous, passiva | `(0,1,0)` | sem batentes, rad |
| `slide_left_middle_link` | 0.200734 | Aço | `slide_left_middle_joint`: fixed / prismatic opcional | — / `(1,0,0)` | fixa / `[0,0.25] m` |
| `slide_left_inner_link` | 0.108548 | Aço | `slide_left_inner_joint`: fixed / prismatic opcional | — / `(1,0,0)` | fixa / `[0,0.25] m` |
| `slide_right_middle_link` | 0.200733 | Aço | `slide_right_middle_joint`: fixed / prismatic opcional | — / `(1,0,0)` | fixa / `[0,0.25] m` |
| `slide_right_inner_link` | 0.108548 | Aço | `slide_right_inner_joint`: fixed / prismatic opcional | — / `(1,0,0)` | fixa / `[0,0.25] m` |
| `tool0` | 0, referencial | sem material físico | `tool0_joint`: fixed | — | fixa |

`link_summary.csv` contém a mesma informação em formato tabular, acrescentando pai, esforço, velocidade, amortecimento e atrito. A soma usa as massas sem arredondamento do YAML.

As ramificações cinemáticas são:

```text
base_link
  -> left_wheel_link
  -> right_wheel_link
  -> caster_<corner>_fork_link -> caster_<corner>_wheel_link  (quatro cantos)
  -> slide_left_middle_link -> slide_left_inner_link -> tool0
  -> slide_right_middle_link -> slide_right_inner_link
```

`tool0` é apenas um referencial na ponta da corrediça interna esquerda, sem inércia, visual ou colisão. Não foi identificada garra, ferramenta atuada ou mecanismo ligando as pontas dos dois trilhos. Os trilhos esquerdo/direito não foram acoplados por `mimic`, e seu deslocamento opcional não implica um mecanismo físico confirmado.

| Família de junta | Esforço máximo declarado | Velocidade máxima | Damping | Friction |
| --- | ---: | ---: | ---: | ---: |
| Rodas motrizes | 12 N·m | 12 rad/s | 0.03 N·m·s/rad | 0.01 N·m |
| Giro dos garfos dos rodízios | 2 N·m | 20 rad/s | 0.002 N·m·s/rad | 0.001 N·m |
| Rodas dos rodízios | 2 N·m | 40 rad/s | 0.002 N·m·s/rad | 0.001 N·m |
| Corrediças, se articuladas | 50 N | 0.1 m/s | 10 N·s/m | 2 N |

Esses parâmetros são valores iniciais de simulação. Não há identificação de motores, redução, torque nominal, corrente, controle embarcado ou velocidade real no CAD analisado. Os limites de esforço nas juntas passivas não representam motores instalados. O curso de 0,25 m por estágio e o sentido de extensão +X das corrediças são hipóteses, não limites extraídos de mates. Os limites declarados no URDF e nas interfaces devem ser verificados no backend escolhido; não constituem garantia independente de proteção do equipamento real.

## Centro de massa e tensor de inércia

No modo padrão `inertia_mode:=mesh`, cada peça usa o volume fechado ou o proxy identificado acima para calcular seu CoM e tensor centroidal. Para agrupar peças num elo:

```text
M = soma(m_i)
c = soma(m_i c_i) / M
d_i = c_i - c
I_C = soma[I_i + m_i ((d_i · d_i) E - d_i d_i^T)]
```

`E` é a matriz identidade 3×3; `I_i` já está expresso no mesmo sistema de eixos ROS. Isso aplica o teorema dos eixos paralelos entre o centro de massa de cada peça e o CoM do elo composto. A rotação CAD foi aplicada à geometria antes do cálculo; equivalentemente, um tensor previamente calculado seria transformado por `R I R^T`.

Os seis elementos `ixx`, `ixy`, `ixz`, `iyy`, `iyz`, `izz` e o `com` local completos de cada elo estão em `config/cad_parameters.yaml`. `inertial_tensor` os escreve com `<origin xyz="CoM" rpy="0 0 0"/>`: o tensor é calculado no CoM e expresso em eixos paralelos aos do elo. Os termos fora da diagonal são elementos do tensor, não produtos geométricos sem sinal. **Não se soma novamente `m d²` para deslocar esse tensor à origem do elo**; o URDF já descreve o deslocamento por `inertial/origin`.

As macros analíticas usam sólidos homogêneos e tensores centroidais:

```text
Caixa de dimensões totais x,y,z:
  Ixx = m(y²+z²)/12, Iyy = m(x²+z²)/12, Izz = m(x²+y²)/12
Cilindro de raio r, comprimento L, eixo local Z:
  Ixx = Iyy = m(3r²+L²)/12, Izz = mr²/2
Esfera maciça de raio r:
  Ixx = Iyy = Izz = 2mr²/5
Nos referenciais de simetria acima: Ixy = Ixz = Iyz = 0.
```

`xyz` e `rpy` orientam/posicionam o referencial inercial da macro, permitindo, por exemplo, alinhar o cilindro ao eixo Y da roda com `rpy=(π/2,0,0)`. `inertia_mode:=primitive` conserva a massa e o CoM CAD, mas substitui o tensor por uma caixa ou cilindro equivalente com as dimensões cadastradas. Esse modo serve para comparar sensibilidade à aproximação; o modo `mesh` conserva a distribuição geométrica calculada. Os fatores positivos de massa multiplicam também o tensor do grupo, mantendo o CoM; não substituem a revisão de uma distribuição de massa interna incorreta.

## Geometrias, contato e atuação

As malhas visuais foram concatenadas por par `(elo, material)`, sem alterar a montagem, e são referenciadas por `package://hema_description/meshes/`. São malhas detalhadas para aparência; os proxies de volume dos STL abertos não substituem seus visuais. Colisões usam caixas para a base/corrediças e cilindros para as seis rodas. Os garfos não têm colisão para evitar preencher o vão da roda com uma caixa. A base usa um envelope conservador que não preserva suas cavidades internas. Essa simplificação limita interações com objetos atravessando vãos e com obstáculos tocando garfos.

`gazebo_config.xacro` concentra atrito, contato, material Classic e controle. Valores iniciais: `wheel_mu=0.9`, `caster_mu=0.5`, base `mu=0.5`, sem autocolisão nos elos de contato. `contact_kp=100000` e `contact_kd=100` são configurações do ramo Classic/ODE; não há promessa de equivalência desses parâmetros no Harmonic. Os mundos usam passo de 0,001 s e gravidade `(0,0,-9.81)`.

O controle entregue é ROS 2 em ambos os simuladores: `gz_ros2_control/GazeboSimSystem` no Harmonic e `gazebo_ros2_control/GazeboSystem` no Classic. Classic não implica ROS 1 neste pacote. Apenas `left_wheel_joint` e `right_wheel_joint` recebem interface de comando, selecionável entre `velocity`, `position` e `effort`, e estados `position`, `velocity`, `effort`. As juntas passivas recebem apenas estados, incluindo corrediças quando articuladas; `hold_joints=false` permite seu movimento passivo.

Os YAML selecionam o controlador correspondente à interface das rodas. O modelo não contém transmissão eletromecânica identificada, drivers reais ou controle de sensores. Módulos CAD de ultrassom são geometria/massa; não foram inferidos alcance, ruído ou tópicos de sensores. Orientações de compilação, inicialização e a extensão dos testes executados são descritas no README do pacote.
