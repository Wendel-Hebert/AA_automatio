import requests
import json
import time
import os
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

# Método de agendamento:
METODO_AGENDAMENTO = "v3_deploy"

# INPUTS DO BOT - nomes devem ser exatamente iguais aos do bot no Control Room
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


def converter_bot_input_para_api(inputs: dict):
    """Formato API AA: type + string|number|boolean (number como string)"""
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
# INPUT DATA + HORÁRIO (COM TIMEZONE REAL)
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

        # conversão REAL para UTC
        execucao_utc = execucao_brt.astimezone(ZoneInfo("UTC"))

        print("Convertido (UTC):", execucao_utc)

        return execucao_utc

    except ValueError:
        raise Exception("Formato inválido. Use DD/MM/AAAA HH:MM")

# ==================================================
# MÉTODO v3_deploy: Aguarda horário e executa via v3/automations/deploy
# ==================================================
# Usa a API que funciona (igual run_rpa_v3), mas aguarda o horário antes de executar.
# O script precisa permanecer aberto até o horário.

def aguardar_e_executar(token, horario_utc):
    br_tz = ZoneInfo("America/Sao_Paulo")
    agora = datetime.now(ZoneInfo("UTC"))

    if horario_utc <= agora:
        raise Exception("Horário já passou.")

    segundos_espera = (horario_utc - agora).total_seconds()
    horario_brt = horario_utc.astimezone(br_tz)

    print(f"\nAguardando até {horario_brt.strftime('%d/%m/%Y %H:%M')} BRT ({segundos_espera:.0f}s)...")
    print("(Mantenha este terminal aberto.)\n")

    time.sleep(segundos_espera)

    print("Horário atingido! Reautenticando e executando bot...")
    token = autenticar()

    url = f"{BASE_URL}/v3/automations/deploy"
    headers = {"X-Authorization": token, "Content-Type": "application/json"}
    device_id = DEVICE_ID
    run_as = RUN_AS_USER_ID
    body = {
        "fileId": FILE_ID,
        "deviceIds": [device_id],
        "runAsUserIds": [run_as],
        "botInput": converter_bot_input_para_api(bot_inputs),
    }

    print("\nPayload:", json.dumps(body, indent=2))

    response = requests.post(url, json=body, headers=headers)
    print("\nStatus:", response.status_code)
    print("Resposta:", response.text)

    if response.status_code not in (200, 201):
        raise Exception("Falha ao executar bot")

    print("\nBOT EXECUTADO COM SUCESSO!")


# ==================================================
# MÉTODO v2_schedule: API v2/schedule/automations (pode dar 500)
# ==================================================

def agendar_via_api(token, horario_utc):
    url = f"{BASE_URL}/v2/schedule/automations"
    headers = {"X-Authorization": token, "Content-Type": "application/json"}
    body = {
        "schedule": {
            "status": "ACTIVE",
            "scheduleType": "NONE",
            "timeZone": "UTC",
            "startDate": horario_utc.strftime("%Y-%m-%d"),
            "startTime": horario_utc.strftime("%H:%M"),
            "repeatEnabled": False,
            "misfireScheduleConfig": False,
            "scheduleResiliency": {
                "common": {
                    "detectAndNotify": {"enabled": False, "hideSensitiveInformation": False},
                    "recording": {"enabled": False, "botStatus": "FAILED"},
                    "handleUnexpectedPopups": True,
                }
            },
        },
        "deployment": {
            "botId": FILE_ID,
            "automationName": f"Execucao_{FILE_ID}_API",
            "description": f"Agendamento via API - Bot {FILE_ID}",
            "botLabel": "",
            "automationPriority": "PRIORITY_MEDIUM",
            "botInput": converter_bot_input_para_api(bot_inputs),
            "runElevated": False,
            "hideBotAgentUi": True,
            "unattendedRequest": {
                "runAsUserIds": [str(RUN_AS_USER_ID)],
                "poolIds": [],
                "numOfRunAsUsersToUse": "1",
                "deviceUsageType": "RUN_ONLY_ON_DEFAULT_DEVICE",
            },
        },
    }

    print("\nPayload:", json.dumps(body, indent=2))
    response = requests.post(url, json=body, headers=headers)
    print("\nStatus:", response.status_code)
    print("Resposta:", response.text)

    if response.status_code not in (200, 201):
        raise Exception("Falha ao agendar")

    print("\nBOT AGENDADO COM SUCESSO!")


# ==================================================
# MAIN
# ==================================================

if __name__ == "__main__":
    token = autenticar()
    horario_utc = solicitar_data_horario()

    if METODO_AGENDAMENTO == "v3_deploy":
        aguardar_e_executar(token, horario_utc)
    else:
        agendar_via_api(token, horario_utc)