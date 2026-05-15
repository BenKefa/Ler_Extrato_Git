import dash
from dash import html, dcc, Input, Output
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import pandas as pd
import base64
import io
from PyPDF2 import PdfReader

# ===== Iniciar o app ===== #
external_stylesheets = [
    dbc.themes.BOOTSTRAP,
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css'
]

external_scripts = [
    'https://cdn.jsdelivr.net/npm/date-fns@4.1.0/locale/pt/cdn.min.js'
]

app = dash.Dash(
    external_stylesheets=external_stylesheets,
    external_scripts=external_scripts,
    suppress_callback_exceptions=True
)

app.title = 'Leitura de extratos bancários'
server = app.server

# Layout do app
app.layout = dbc.Container(
    fluid=True,
    style={"backgroundColor": "#f5f6fa", "padding": "20px"},
    children=[
        html.H2("Upload de PDF e Visualização", className="text-center mb-4 text-primary"),

        # Seção PICPAY
        dbc.Card(
            style={"marginBottom": "30px", "padding": "20px", "boxShadow": "0 4px 8px rgba(0,0,0,0.1)"},
            children=[
                html.H4("Extrato PICPAY", className="text-center text-info mb-3"),

                # Upload
                dcc.Upload(
                    id="upload-pdf-picpay",
                    children=html.Div(["Clique ou arraste para enviar PDF do PICPAY"]),
                    style={
                        "width": "100%", "height": "60px", "lineHeight": "60px",
                        "borderWidth": "1px", "borderStyle": "dashed", "borderRadius": "5px",
                        "textAlign": "center", "margin": "10px", "backgroundColor": "#eaf4ff"
                    },
                    multiple=False
                ),

                # KPIs
                dbc.Row([
                    dbc.Col(dbc.Card(
                        dbc.CardBody([
                            html.I(className="fas fa-money-bill-wave text-primary", style={"fontSize": "30px"}),
                            html.H6("Total Gastos"),
                            html.H4(id="total_gastos_picpay", className="fw-bold text-primary")
                        ])
                    ), md=6),

                    dbc.Col(dbc.Card(
                        dbc.CardBody([
                            html.I(className="fas fa-store text-success", style={"fontSize": "30px"}),
                            html.H6("Estabelecimento mais frequente"),
                            html.H4(id="valor_gastos_picpay", className="fw-bold text-success")
                        ])
                    ), md=6),
                ], justify="center", className="mb-3"),

                # Grid + Gráficos lado a lado
                dbc.Row([
                    dbc.Col(
                        dag.AgGrid(
                            id="grid-extrato-picpay",
                            rowData=[],
                            columnDefs=[],
                            defaultColDef={"sortable": True, "filter": True, "resizable": True},
                            style={"height": "500px", "width": "100%"},
                        ),
                        md=6
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody([
                                dcc.Graph(id="grafico_picpay_1", style={"height": "240px"}),
                                dcc.Graph(id="grafico_picpay_2", style={"height": "240px", "marginTop": "20px"})
                            ])
                        ),
                        md=6
                    )
                ])
            ]
        ),
    ]
)

# ===== Função para ler PDF PICPAY ===== #
def pdf_para_dataframe_picpay(contents):
    """Extrai texto do PDF e retorna DataFrame estruturado (Data, Estabelecimento, Valor)"""
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    pdf = PdfReader(io.BytesIO(decoded))

    todas_linhas = []
    for page in pdf.pages:
        texto = page.extract_text()
        if texto:
            todas_linhas.extend(texto.split("\n"))

    # Encontrar índice da linha de cabeçalho
    idx_cabecalho = None
    for i, linha in enumerate(todas_linhas):
        if "Data" in linha and "Estabelecimento" in linha and "Valor" in linha:
            idx_cabecalho = i
            break

    registros = []
    if idx_cabecalho is not None:
        for linha in todas_linhas[idx_cabecalho+1:]:
            partes = linha.strip().split()
            if len(partes) >= 3:
                data = partes[0]
                valor_str = partes[-1].replace("R$", "").replace(".", "").replace(",", ".").strip()
                estabelecimento = " ".join(partes[1:-1])

                if "/" not in data:
                    continue

                try:
                    valor_float = float(valor_str)
                    registros.append({
                        "Data": data,
                        "Estabelecimento": estabelecimento,
                        "Valor (R$)": valor_float
                    })
                except ValueError:
                    continue

    return pd.DataFrame(registros, columns=["Data", "Estabelecimento", "Valor (R$)"])





# ===== Callback PICPAY ===== #
@app.callback(
    Output('total_gastos_picpay', 'children'),
    Output('valor_gastos_picpay', 'children'),
    Output('grafico_picpay_1', 'figure'),
    Output('grafico_picpay_2', 'figure'),
    Output("grid-extrato-picpay", "rowData"),
    Output("grid-extrato-picpay", "columnDefs"),
    Input("upload-pdf-picpay", "contents"),
    prevent_initial_call=True
)
def atualizar_picpay(conteudo_extrato_picpay):
    if conteudo_extrato_picpay is None:
        return "0", "-", [], []

    extrato = pdf_para_dataframe_picpay(conteudo_extrato_picpay)
    extrato = extrato[extrato['Estabelecimento'] != "PAGAMENTO DE FATURA"]


    if extrato.empty:
        return "0", "-", [], []

    # Total de gastos
    total_gastos = f"{extrato['Valor (R$)'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Estabelecimento mais frequente
    valor_gastos = extrato["Estabelecimento"].mode().values[0]
    
    # Gráficos de gastos por dia
    gastos_por_data = extrato.groupby("Data")["Valor (R$)"].sum().reset_index()
    
    grafico_picpay_1 = go.Figure(go.Scatter(x=gastos_por_data['Data'], y=gastos_por_data['Valor (R$)'])).update_layout(title='Gastos por dia')
    grafico_picpay_1.update_layout(margin=dict(l=5, r=5, t=40, b=5), yaxis_title='', xaxis_title='', title_x=0.5, hovermode='closest', dragmode=False).update_traces(hoverinfo='all')

    gastos_por_estabelecimento = extrato.groupby("Estabelecimento")["Valor (R$)"].sum().reset_index()

    grafico_picpay_2 = go.Figure(go.Bar(x=gastos_por_estabelecimento['Estabelecimento'], y=gastos_por_estabelecimento['Valor (R$)'])).update_layout(title='Gastos por estabelecimento')
    grafico_picpay_2.update_layout(margin=dict(l=5, r=5, t=40, b=5), yaxis_title='', xaxis_title='', title_x=0.5, hovermode='closest', dragmode=False).update_traces(hoverinfo='all')

    # GRID de gastos por data e estabelecimento
    rowData = extrato.to_dict("records")
    columnDefs = [{"headerName": col, "field": col} for col in extrato.columns]

    return total_gastos, valor_gastos, grafico_picpay_1, grafico_picpay_2, rowData, columnDefs


# ===== Iniciar o servidor ===== #
if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8052, debug=False)
