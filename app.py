import streamlit as st
import json

# Define o título da página do seu aplicativo
st.title("Sistema de Gestão de Empresas")

# Abre o arquivo JSON que você acabou de criar e lê os dados
with open('empresas.json', 'r', encoding='utf-8') as arquivo:
    lista_de_empresas = json.load(arquivo)

# Avisa na tela que deu tudo certo e mostra quantas empresas achou
st.success(f"Conseguimos ler o arquivo! Encontramos {len(lista_de_empresas)} empresas.")

# Mostra a lista completa de dados na tela do seu aplicativo
st.json(lista_de_empresas)
