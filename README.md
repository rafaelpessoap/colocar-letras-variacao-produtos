# Editor de Mapeamento Interativo YOLO26

Um aplicativo desktop desenvolvido em Python (PyQt6) criado especificamente para mapear e identificar miniaturas ou estátuas em imagens, rotulando-as automaticamente com letras sequenciais (A, B, C, etc.). 

O aplicativo foca em manter **100% da qualidade original** da imagem gerada, oferecendo uma interface interativa de arrastar e soltar (Drag & Drop) nativa do macOS para revisar e editar a posição das etiquetas geradas pela IA antes do salvamento final.

## 🚀 Principais Funcionalidades

- **Detecção Híbrida Inteligente:** Utiliza um algoritmo super rápido baseado em **OpenCV** para imagens com fundo limpo/sólido. Caso a imagem seja muito complexa ou não gere bons resultados imediatos, atua como fallback para os modelos avançados **YOLO26**.
- **Modelos YOLO Selecionáveis:** Alternância livre na interface entre os modelos `yolo26n.pt` (rápido), `yolo26s`, `yolo26m`, `yolo26l` e `yolo26x.pt` (máxima precisão). O download dos pesos pesados é administrado automaticamente pelo App.
- **Edição Livre:** As letras inseridas pela IA não são "chumbadas" na imagem logo de cara. Elas são instâncias gráficas interativas:
  - Arraste livremente qualquer letra com o mouse para reposicionar.
  - Selecione letras erradas e pressione **Delete** ou **Backspace**.
  - Pressione o botão **Adicionar Letra (+)** para adicionar letras que a IA tenha deixado passar.
- **Reorganização Automática:** Botão **"↻ Reordenar Letras"** avalia a posição `X` de todas as letras dispostas no quadro e recalcula as nomenclaturas (A, B, C, D...) ordenadamente do canto esquerdo da tela para o canto direito.
- **Preservação de Resolução:** Processamento de salvamento via biblioteca *Pillow (PIL)* que re-renderiza individualmente cada caractere sobre a matriz original da foto impedindo qualquer compressão visual provocada pelas ferramentas de interface gráfica.
- **Navegação Canvas:** Suporte embutido do macOS à ferramenta de **Zoom In (+)** e **Zoom Out (-)**, gerando barras de rolagem nativas para lidar com detalhes profundos nas artes ou fotografias importadas.

## 💻 Instalação (Desenvolvedores)

O projeto exige **Python 3.10+**. 
Para rodar localmente no seu computador através da IDE ou Terminal:

```bash
# Clone o repositório
git clone https://github.com/rafaelpessoap/colocar-letras-variacao-produtos.git
cd colocar-letras-variacao-produtos

# Crie e ative um ambiente virtual (Opcional, mas recomendado)
python -m venv venv
source venv/bin/activate

# Instale os requerimentos
pip install -r requirements.txt

# Inicie o aplicativo
python main.py
```

## 📦 Uso via macOS
O repositório inclui a compilação local (encapsulamento de shell interno via formato `.app` - `Aplicativo Letras.app`). Caso esteja no macOS com o ambiente configurado, você pode apenas clicar duas vezes no App para abrir seu visualizador nativo limpo sem uso explícito de Terminal do sistema!

## 💡 Fluxo de Vida do Arquivo
1. Arraste uma imagem (`.jpg`, `.jpeg`, ou `.png`) para a tela principal da aplicação.
2. Analise a rotulação automática baseada no modelo selecionado.
3. Arraste letras, limpe incorretas, ou altere nomes/fontes dando re-order.
4. Salve o arquivo. A nova imagem será gerada idêntica a de entrada finalizada com o sulfixo `_` (e.g. `MiniaturaMagico_.jpg`). Imagens transparentes em `.png` recebem fundo branco limpo.
