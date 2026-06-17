# Dados

Esta pasta guarda os dados de questões do ENEM usados pelo benchmark. O conteúdo baixado ou gerado
não é versionado, ele é recriado a partir das fontes abaixo.

O projeto tem duas fontes de dados, ambas devolvendo o mesmo `schema.Questao`:

## Fonte padrão: PDFs oficiais do INEP (ENEM 2025)

- **Fonte:** cadernos de prova e gabarito publicados pelo INEP, provas públicas do ENEM.
  Disponíveis em downloads.inep.gov.br e nas páginas do ENEM em www.gov.br/inep.
- **Licença:** material público do governo federal (INEP). As provas do ENEM são divulgadas
  publicamente após a aplicação.
- **Arquivos usados (2025, caderno Azul):**
  - `enem/2025_PV_impresso_D1_CD1.pdf` e `enem/2025_GB_impresso_D1_CD1.pdf` (Dia 1, Caderno 1)
  - `enem/2025_PV_impresso_D2_CD7.pdf` e `enem/2025_GB_impresso_D2_CD7.pdf` (Dia 2, Caderno 7)
- **Cobertura:** as **quatro áreas**. Dia 1, questões 1 a 90, Linguagens e Ciências Humanas. Dia 2,
  questões 91 a 180, Ciências da Natureza e Matemática. Carrega-se cada dia com `carregar_prova_pdf`
  passando `dia=1` ou `dia=2`.
- **Questões anuladas:** o gabarito do Dia 2 traz algumas questões marcadas como "Anulado", sem
  resposta válida. Elas são excluídas, pois não há como pontuar. Em 2025 foram 3 (123, 132 e 174),
  então o Dia 2 tem 87 questões válidas.
- **Idioma estrangeiro:** as questões 1 a 5 (Dia 1) têm versão em inglês e em espanhol. Por padrão
  usamos a versão em **inglês** (parâmetro `lingua` em `carregar_prova_pdf`).
- **Imagens das questões:** a prova vem em duas colunas e muitas questões têm figura, sobretudo no
  Dia 2 (gráficos e figuras geométricas). O parser lê o texto coluna a coluna por coordenada e, para
  as questões com figura, recorta a imagem para um PNG em `data/figures/<ano>/dia<dia>/`. A detecção
  cobre figuras raster (fotos, cartazes, infográficos) e desenhos vetoriais (gráficos, mapas, figuras
  geométricas), separando figura de moldura de caixa de texto pela fração de texto dentro da região.
  Em 2025 são 17 questões com figura no Dia 1 e 44 no Dia 2.
- **Limitação conhecida:** poucas questões de Matemática têm as alternativas como fórmulas em imagem,
  que o pdfplumber não lê como texto. Nesses casos as alternativas saem vazias ou ruidosas. São
  poucas e ficam documentadas aqui.

A pasta `enem/` com os PDFs originais não é versionada, por serem arquivos grandes e recriáveis a
partir da fonte pública. Quem clonar baixa os PDFs do INEP e os coloca em `enem/`.

Implementado em `src/enembench/pdf_enem.py`.

## Fonte opcional: maritaca-ai/enem (Hugging Face)

- **Dataset:** [maritaca-ai/enem](https://huggingface.co/datasets/maritaca-ai/enem).
- **Licença:** Apache 2.0, declarada no card do dataset.
- **Anos cobertos:** ENEM 2022, 2023 e 2024, 180 questões por ano, com as quatro áreas.
- **Imagens:** flag `IU`, coluna `figures` com URLs e `description` com a descrição textual.
- **Uso:** mantida como fonte alternativa, útil para cobrir as quatro áreas com 2022 a 2024 enquanto
  o ENEM 2025 só tem o Dia 1. Implementada em `src/enembench/dataset.py`.

## Derivação da área

Nenhuma das fontes traz a área explícita, então derivamos do número da questão, pela estrutura fixa
do ENEM (`src/enembench/normalizacao.py`):

- questões **1 a 45**: Linguagens
- questões **46 a 90**: Ciências Humanas
- questões **91 a 135**: Ciências da Natureza
- questões **136 a 180**: Matemática
