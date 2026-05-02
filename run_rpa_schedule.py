import requests
import json
import os
import time
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo


# ==================================================
# CONFIGURAÇÕES
# ==================================================

load_dotenv(override=True)

BASE_URL = os.getenv("BASE_URL")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
FILE_ID = int(os.getenv("FILE_ID"))
DEVICE_ID = int(os.getenv("DEVICE_ID"))
RUN_AS_USER_ID = int(os.getenv("RUN_AS_USER_ID"))


# INPUTS DO BOT
bot_inputs = {
    "bolManual": True,
    "bolUploadClarity": False,
    "credPasswordManual": "credPasswordManual",
    "numAgenteCHESF": 1,
    "numAgenteELET": 0,
    "numAgenteENOR": 0,
    "numAgenteESUL": 0,
    "numAgenteFURNAS": 0,
    "numTipoFormulario": 4,
    "strCiclo": "2025",
    "strEmailDestinatarioManual": "email@empresa.com",
    "strEmpresa": "1",
    "strUsernameManual": "main.bot",
}


# ===========================================================
# CONVERSÃO INPUTS EVITANDO BLOQUEIO DE TIPOS DE DADOS NA API
# ===========================================================

def converter_bot_input_para_api(inputs: dict):
    resultado = {}

    for chave, valor in inputs.items():
        if isinstance(valor, bool):
            resultado[chave] = {"type": "BOOLEAN", "boolean": valor}
        elif isinstance(valor, (int, float)):
            resultado[chave] = {"type": "NUMBER", "number": str(int(valor))}
        else:
            resultado[chave] = {"type": "STRING", "string": str(valor)}

    return resultado


# ==================================================
# LOGIN
# ==================================================

def autenticar():
    print("Autenticando...")

    response = requests.post(
        f"{BASE_URL}/v2/authentication",
        json={
            "username": USERNAME,
            "password": PASSWORD
        },
        headers={"Content-Type": "application/json"}
    )

    if response.status_code != 200:
        print(response.text)
        raise Exception("Falha no login")

    print("Login realizado")
    return response.json()["token"]


# ==================================================
# INPUT DATA/HORA
# ==================================================

def solicitar_data_horario():
    print("\nInforme a DATA e HORÁRIO de execução (HORÁRIO BRASIL)")
    print("Formato: DD/MM/AAAA HH:MM")
    print("Exemplo: 25/03/2026 14:30\n")

    entrada_usuario = input("Data e horário desejados: ")

    try:
        br_tz = ZoneInfo("America/Sao_Paulo")

        execucao_brt = datetime.strptime(
            entrada_usuario,
            "%d/%m/%Y %H:%M"
        ).replace(tzinfo=br_tz)

        agora_brt = datetime.now(br_tz)

        if execucao_brt <= agora_brt:
            raise Exception("Não é possível agendar para uma data passada.")

        print("Agendado (BRT):", execucao_brt)

        execucao_utc = execucao_brt.astimezone(ZoneInfo("UTC"))

        print("Convertido (UTC):", execucao_utc)

        return execucao_utc

    except ValueError:
        raise Exception("Formato inválido. Use DD/MM/AAAA HH:MM")


# ==================================================
# AGENDAMENTO (SEM BLOQUEIO) SCRIPT RODA POREM ROBO SO RODA NO HORARIO AGENDADO, TESTADO COM SUCESSO COM BOT INPUTS ENVIADOS VIA API
# ==================================================

def agendar_via_api(token, horario_utc):
    url = f"{BASE_URL}/v2/schedule/automations"

    headers = {
        "X-Authorization": token,
        "Content-Type": "application/json"
    }

    body = {
        "schedule": {
            "name": f"Agendamento_{FILE_ID}_{int(time.time())}",
            "description": "Agendamento via API",
            "scheduleType": "ONCE",
            "status": "ACTIVE",
            "timeZone": "UTC",
            "startDate": horario_utc.strftime("%Y-%m-%d"),
            "startTime": horario_utc.strftime("%H:%M"),
            "repeatEnabled": False
        },
        "deployment": {
            "botId": FILE_ID,
            "automationName": f"Execucao_{FILE_ID}",
            "botInput": converter_bot_input_para_api(bot_inputs),
            "runElevated": False,
            "hideBotAgentUi": True,
            "automationPriority": "PRIORITY_MEDIUM",
            "unattendedRequest": {
                "runAsUserIds": [RUN_AS_USER_ID],
                "deviceIds": [DEVICE_ID],
                "numOfRunAsUsersToUse": 1
            }
        }
    }

    print("\nPayload:")
    print(json.dumps(body, indent=2))

    response = requests.post(url, json=body, headers=headers)

    print("\nStatus:", response.status_code)
    print("Resposta:", response.text)

    if response.status_code not in (200, 201):
        raise Exception("Falha ao agendar bot")

    print("\n BOT AGENDADO COM SUCESSO!")


# ==================================================
# MAIN
# ==================================================

if __name__ == "__main__":
    token = autenticar()
    horario_utc = solicitar_data_horario()
    agendar_via_api(token, horario_utc)