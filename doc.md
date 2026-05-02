# Agendamento de Bots via API - Automation Anywhere

## Visão Geral

Este projeto tem como objetivo realizar o **agendamento de execuções de bots no Automation Anywhere** de forma programática, utilizando a API oficial do Control Room.


### Solução adotada

O script implementa um fluxo correto de agendamento:

* o usuário passa parâmetros de entrada 
* O usuário informa data e hora (em BRT)
* O sistema converte automaticamente para UTC
* A execução é **agendada diretamente no Control Room**
* O script **finaliza imediatamente**, sem bloquear recursos

---


## Arquitetura do Fluxo

```text
[Início Script]
      ↓
Carrega variáveis (.env)
      ↓
Autentica na API
      ↓
Solicita parâmetros de entrada 
      ↓
Verifica formato esperado pela API
      ↓
Solicita data/hora (BRT)
      ↓
Valida data futura
      ↓
Converte para UTC
      ↓
Monta payload
      ↓
Chama API de agendamento
      ↓
Recebe resposta (201)
      ↓
Finaliza execução
```

---

## Tecnologias Utilizadas

* Python 3.10+
* requests
* python-dotenv
* zoneinfo (timezone nativo)

---

## Variáveis de Ambiente

Crie um arquivo `.env` com as seguintes variáveis:

```env
BASE_URL=https://seu-control-room
USERNAME=seu_usuario
PASSWORD=sua_senha
FILE_ID=ID_DO_BOT
DEVICE_ID=ID_DO_DEVICE
RUN_AS_USER_ID=ID
```

## Autenticação Do Script 

```
POST /v2/authentication
```

#### Função 
```
autenticar()
```
* Envia credenciais
* Recebe token JWT
* Utiliza token nas chamadas seguintes

---
## Agendamento do Bot

```
POST /v2/schedule/automations
```
#### Função 

```
agendar_via_api()
```
---

## Estrutura do Payload

```
{
  "scheduleType": "ONCE",
  "status": "ACTIVE",
  "timeZone": "UTC",
  "startDate": "YYYY-MM-DD",
  "startTime": "HH:MM",
  "repeatEnabled": false
}
```
---

## Deployment 
```
{
  "botId": FILE_ID,
  "automationName": "Execucao_{FILE_ID}",
  "botInput": {...},
  "unattendedRequest": {
    "runAsUserIds": [RUN_AS_USER_ID],
    "deviceIds": [DEVICE_ID],
    "numOfRunAsUsersToUse": 1
  }
}
```

### Desenvolvedor
```
H. Wendel Feitosa
```