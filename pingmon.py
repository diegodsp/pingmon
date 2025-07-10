import platform
import subprocess
import time

from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

DESTINOS = {
    "Local Gateway": "10.20.0.1",
    "Google Brasil": "8.8.8.8",
    "Cloudflare USA": "1.1.1.1",
    "OVH França": "188.165.12.106",
}

INTERVALO_SEGUNDOS = 2
TIMEOUT_MS = 1000
LIMITE_LATENCIA = 150  # alerta acima disso

console = Console()
sistema = platform.system()


def ping(host: str):
    if sistema == "Windows":
        cmd = ["ping", "-n", "1", "-w", str(TIMEOUT_MS), host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(int(TIMEOUT_MS / 1000)), host]

    try:
        saida = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
        if "unreachable" in saida.lower():
            return None, "Inacessível"
        tempo = None
        for linha in saida.splitlines():
            if "time=" in linha:
                tempo = float(linha.split("time=")[1].split()[0].replace("ms", "").replace("<", ""))
                return tempo, "OK"
            elif "round-trip" in linha and "/" in linha:
                partes = linha.split("=")[1].strip().split("/")
                if len(partes) >= 2:
                    tempo = float(partes[1])  # média (avg)
                    return tempo, "OK"
        return None, "Sem resposta"
    except subprocess.CalledProcessError:
        return None, "Timeout"


def gerar_tabela(resultados):
    tabela = Table(title="Monitor de Ping", box=box.SIMPLE_HEAVY)
    tabela.add_column("Destino", justify="left")
    tabela.add_column("Endereço", justify="left")
    tabela.add_column("Status", justify="center")
    tabela.add_column("Tempo (ms)", justify="right")

    for nome, (ip, tempo, status) in resultados.items():
        if status == "OK" and tempo is not None:
            cor = "green" if tempo < LIMITE_LATENCIA else "yellow"
            tabela.add_row(nome, ip, f"[{cor}]✔ {status}[/{cor}]", f"[{cor}]{tempo:.0f}ms[/{cor}]")
        else:
            tabela.add_row(nome, ip, "[red]✖ " + status + "[/red]", "[red]--[/red]")
    return tabela


def monitorar():
    with Live(refresh_per_second=1) as live:
        while True:
            resultados = {}
            ocorrencias = []
            for nome, ip in DESTINOS.items():
                tempo, status = ping(ip)
                resultados[nome] = (ip, tempo, status)
                if status != "OK":
                    ocorrencias.append(f"{nome} ({ip}) - {status}")

            tabela = gerar_tabela(resultados)
            if ocorrencias:
                falhas_texto = "\n".join(f"- {oc}" for oc in ocorrencias)
                painel_falhas = Panel(falhas_texto, title="Ocorrências Graves", style="red", border_style="red")
                live.update(Group(tabela, painel_falhas))
            else:
                live.update(tabela)
            # live.update(gerar_tabela(resultados))
            time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    try:
        console.print("[bold cyan]Iniciando monitoramento de rede... Ctrl+C para sair[/bold cyan]")
        monitorar()
    except KeyboardInterrupt:
        console.print("\n[bold red]Monitoramento encerrado pelo usuário.[/bold red]")
