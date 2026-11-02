# Validação realizada

Data: 21/09/2026. Os resultados completos estão em `validation_xacro.json` e `runtime_classic.json`.

| Verificação | Resultado |
| --- | --- |
| Expansão real com Xacro 2.1.1 | 36 variantes aprovadas: 3 backends × 3 interfaces × 2 configurações de corrediças × 2 modelos de inércia |
| Árvore URDF | 16 links, 15 joints, raiz única `base_link`, sem ciclos ou elos desconectados |
| Massas/tensores | Positivos e finitos; tensores definidos positivos; desigualdade triangular dos momentos principais satisfeita |
| Escala de massa | Massa e tensor escalam linearmente; CoM preservado |
| Malhas | Todos os URI `package://` resolvidos para arquivos presentes; escala em metros |
| Cinemática | Origens conferidas com os dados CAD; eixos unitários e limites válidos |
| Contatos | Seis rodas coplanares com a correção padrão dos rodízios |
| Controle | Duas juntas atuadas; oito passivas com estado, mais quatro quando as corrediças são liberadas |
| Build ROS 2 Humble | `colcon build` aprovado em Ubuntu 22.04/WSL |
| Conversão Gazebo Classic | `gz sdf -p` e `gz sdf -k` aprovados |
| Execução Gazebo Classic 11.10.2 | Inserção do modelo e inicialização do plugin aprovadas |
| Controladores | `joint_state_broadcaster` e `wheel_controller` ativos |
| Movimento | Comando `[2,2] rad/s`; médias observadas `1.885065` e `1.895437 rad/s` |
| Parada | Médias após comando zero: `-0.00002605` e `-0.00001546 rad/s` |
| Estados e relógio | 709 mensagens de estado; dez juntas móveis presentes; interfaces exportadas finitas; relógio progrediu de 0,1 a 7,7 s |

O teste completo de execução levou aproximadamente 16,31 s de tempo de parede. O critério de acompanhamento foi erro ≤0,5 rad/s; a resposta observada **não comprova rastreamento exato**, odometria ou desempenho do motor real. As juntas passivas exportam posição/velocidade; os NaN de esforço que o broadcaster coloca nessas juntas representam uma interface ausente, não um esforço físico inválido. Esforços das rodas atuadas foram finitos.

A consulta opcional à pose global foi omitida porque o serviço `get_entity_state` não estava disponível no mundo. Não foi realizado teste de estabilidade prolongada, trajetória, carga útil ou autocolisão. Harmonic não foi executado nesta máquina. Posição, esforço, corrediças articuladas e inércias primitivas foram verificados na expansão e consistência do modelo, sem ensaio dinâmico individual.

A execução real identificou e corrigiu duas incompatibilidades de Humble: importação de uma ação `LogError` inexistente e comentários XML que interferiam no parser do plugin Classic. O launch final usa `LogInfo` e remove comentários apenas do XML enviado em `robot_description`; os fontes Xacro mantêm a documentação.

O `robot_state_publisher` pode informar que KDL não usa a inércia da raiz `base_link`. Isso não remove a inércia do Gazebo: o simulador usa a massa/tensor do URDF/SDF. Não foi adicionado vínculo ao mundo para contornar esse aviso.
