# enem-llm-benchmark

Este é um projeto que eu montei para medir quão bem alguns modelos de linguagem respondem às questões
do ENEM, a prova que mais gente presta no Brasil. A ideia central é simples, eu pego as provas
oficiais, mando os modelos responderem, comparo cada resposta com o gabarito e olho não só o acerto
geral, mas também onde cada modelo erra, separando por área do conhecimento. O resultado abaixo é da
edição de 2025, com três modelos gratuitos, e já trouxe um achado que eu não esperava de início.

![Acurácia por modelo e área](mapa_calor_modelo_area.png)

## O que eu quis responder

A pergunta que guia o trabalho é quão longe chegam modelos gratuitos, desses que qualquer pessoa roda
com uma chave de API sem pagar nada, numa prova feita para humanos, e em que tipo de questão eles
tropeçam. Em vez de ficar só com a nota final, que esconde muita coisa, eu quis um retrato por área,
porque é aí que dá para perceber, por exemplo, se um modelo vai bem em interpretação de texto mas
desanda no raciocínio matemático. Para isso o projeto precisou de três peças, uma que transforma a
prova em PDF num conjunto de questões organizadas, uma que conversa com os modelos e guarda as
respostas, e uma que pontua tudo e desenha os gráficos.

## De onde vêm as questões

As questões vêm das provas oficiais do ENEM 2025, divulgadas pelo INEP, que são material público.
Eu uso os cadernos de prova e de gabarito em PDF dos dois dias, o primeiro com Linguagens e Ciências
Humanas, e o segundo com Ciências da Natureza e Matemática, cobrindo as quatro áreas da prova. Tirar
as questões de um PDF, no entanto, deu bastante trabalho, porque a prova vem em duas colunas, e uma
leitura ingênua embaralha a ordem das questões. Eu acabei lendo o texto coluna a coluna por
coordenada, casando cada cabeçalho com a questão certa.

Algumas decisões tiveram que ser registradas com cuidado, para o resultado ser honesto. As questões
1 a 5 do primeiro dia têm versão em inglês e em espanhol, e eu fixei o inglês. As questões anuladas,
que o gabarito do segundo dia marca como tal, ficam de fora, porque não há resposta certa para
pontuar. E muitas questões têm figura, sobretudo em Matemática, então, para os modelos que enxergam
imagem, eu recorto a figura da questão para um arquivo à parte, distinguindo um gráfico de verdade da
moldura de uma simples caixa de texto pela quantidade de texto dentro da região. Toda a procedência e
a licença dos dados estão documentadas no repositório.

## Como eu avalio os modelos

Para cada questão, eu monto um prompt que apresenta o enunciado e as cinco alternativas, e peço que o
modelo explique o raciocínio passo a passo e termine escrevendo a letra escolhida num formato fixo.
Guardar o raciocínio é útil, porque é dele que sai a coletânea de erros comentados, que mostra como o
modelo pensou quando errou. Da resposta crua eu extraio a letra com uma função tolerante, que aguenta
respostas bagunçadas, e comparo com o gabarito.

Os provedores ficam todos atrás de uma interface única, então adicionar um modelo novo é só escrever
um pequeno adaptador e apontar um arquivo de configuração, sem mexer no núcleo. Hoje estão
implementados o Google Gemini, o Groq e o OpenRouter, todos com plano gratuito. Cada resposta vai
para um cache em disco, com chave derivada do modelo, da questão e do prompt, de modo que rodar de
novo reaproveita o que já foi pedido e não gasta cota à toa, o que também torna o resultado estável.

## Os resultados

A rodada que apresento aqui usou três modelos do Groq sobre a prova inteira de 2025, somando 348
respostas de questões de texto, com acurácia geral de 72,1%.

| Modelo | Acurácia geral |
|---|---|
| Llama 3.3 70B | 82,8% |
| GPT-OSS 20B | 75,9% |
| Llama 3.1 8B | 57,8% |

Por área, a ordem de facilidade foi Ciências Humanas, Ciências da Natureza, Linguagens e, bem mais
difícil para todos, Matemática, o que combina com a intuição de quem já fez a prova.

![Acurácia por área, por modelo](acuracia_por_area.png)

O modelo pequeno de 8 bilhões de parâmetros ficou atrás dos outros em todas as áreas, como era de
esperar. O achado interessante, porém, está no mapa de calor lá do começo. O GPT-OSS de 20 bilhões,
que é o menor dos dois maiores, supera o Llama de 70 bilhões justamente em Matemática, 73% contra
64%, mesmo perdendo para ele nas demais áreas. Modelo maior não vence em tudo, e a área mais difícil
da prova acabou premiando o modelo aberto da OpenAI, treinado com foco em raciocínio.

## O que ainda não está perfeito

Vale ser franco sobre os limites, porque eles importam na hora de ler os números. As amostras por
área são pequenas, na casa de algumas dezenas de questões, então cada taxa carrega uma margem de erro
grande, e diferenças de poucos pontos não devem ser superinterpretadas. Este recorte usa apenas
questões de texto, já que os modelos puramente textuais não leem imagem, então as questões com figura
ficaram fora desta comparação. Há ainda um punhado de questões de Matemática em que as alternativas
são fórmulas em imagem, que a extração de texto não consegue ler, e essas saem com alternativas
vazias. E os planos gratuitos têm seus limites, o Gemini estava com a cota zerada nesta conta, e os
modelos do OpenRouter têm teto diário, então o Groq foi o provedor mais estável para uma rodada
inteira.

## Como reproduzir

O ambiente é gerenciado com o [uv](https://docs.astral.sh/uv/). Depois de clonar o repositório e
colocar as chaves gratuitas num arquivo `.env`, a partir do `.env.example`, basta avaliar os modelos
e gerar os relatórios:

```bash
uv sync
uv run enembench --so-texto       # avalia os modelos do config e salva o CSV
uv run enembench-relatorio        # gera os gráficos e os erros comentados
```

O CSV com os resultados está versionado no repositório, então o notebook de análise em
[notebooks/analise.ipynb](https://github.com/LucasSpinola/enem-llm-benchmark/blob/main/notebooks/analise.ipynb)
roda direto e reproduz cada gráfico desta página.

## Os erros comentados

A parte que mais rende para discutir é a coletânea de [erros comentados](erros_comentados.md), que
junta as questões erradas com o raciocínio que cada modelo deu. É lendo esses casos que dá para
entender se o modelo não sabia o conteúdo, se foi mal na conta, ou se a própria extração da questão
atrapalhou.

---

O código está no [repositório](https://github.com/LucasSpinola/enem-llm-benchmark), com testes e
integração contínua. Feito por Lucas Spinola, sob licença MIT.
