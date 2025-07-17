# Controle_medicamentos
Aplicação em Streamlit voltada para o controle de estoque de medicamentos de uso diário.

Como funciona o controle de estoque

* O medicamento **referência** (ex: Aradois) define o ciclo de reposição
* O estoque de todos os medicamentos é **automaticamente reduzido** com base nos dias desde a última atualização
* A lógica de consumo é:

  ```
  novo_estoque = estoque_atual - (dosagem_diária × dias_passados)
  ```
* No **dia da compra** (ex: todo dia 21), o medicamento de referência é **reabastecido automaticamente** com:

  ```
  estoque += 30 × dosagem_diária
  ```
* A data do último ajuste é salva no campo `last_stock_update` do `config.json`
* Medicamentos que ainda têm estoque suficiente **não são recarregados**.

### 💡 Exemplo prático: compra antecipada por promoção

Você pode aproveitar uma promoção e comprar mais unidades de um medicamento (ex: 3 caixas de Atorvastatina com 30 comprimidos cada) sem prejudicar o controle do sistema.

**Como fazer:**

* Abra o aplicativo
* Selecione o medicamento e clique em **✏️ Editar Medicamento**
* Some a quantidade comprada ao estoque atual (ex: 15 + 90 = 105)
* Salve as alterações normalmente

✅ Isso funciona porque:

* O sistema reduz o estoque diariamente com base na dosagem
* Ele só repõe automaticamente o medicamento de referência no dia base de compra
* Os demais permanecem com estoque prolongado até o próximo ciclo necessário