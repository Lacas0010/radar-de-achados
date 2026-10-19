import time
import threading
import urllib.request
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from models.item import Anuncio
from main import buscar_itens

class SentinelaTask:
    def __init__(
        self,
        termo: str,
        uf: str = "df",
        intervalo_minutos: int = 15,
        preco_teto: Optional[float] = None,
        apenas_super_achados: bool = True,
        webhook_url: Optional[str] = None,
        webhook_tipo: str = "discord" # 'discord' ou 'telegram'
    ):
        self.termo = termo
        self.uf = uf
        self.intervalo_minutos = max(intervalo_minutos, 2) # mínimo 2 minutos
        self.preco_teto = preco_teto
        self.apenas_super_achados = apenas_super_achados
        self.webhook_url = webhook_url
        self.webhook_tipo = webhook_tipo.lower()
        
        self.ativo = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        self.ultima_execucao: Optional[str] = None
        self.proxima_execucao: Optional[str] = None
        self.total_alertas_enviados = 0
        self.ultimos_alertas: List[Dict[str, Any]] = []

    def start(self):
        if self.ativo:
            return
        self.ativo = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[Sentinela] Monitoramento iniciado para '{self.termo}' ({self.uf.upper()}) a cada {self.intervalo_minutos}min.")

    def stop(self):
        if not self.ativo:
            return
        self.ativo = False
        self._stop_event.set()
        print(f"[Sentinela] Monitoramento pausado para '{self.termo}'.")

    def _loop(self):
        while not self._stop_event.is_set():
            agora = datetime.now()
            self.ultima_execucao = agora.strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[Sentinela] Executando varredura para '{self.termo}'...")

            try:
                # Busca anúncios com filtro nativo
                anuncios = buscar_itens(
                    termo=self.termo,
                    uf=self.uf,
                    preco_max=self.preco_teto,
                    apenas_novos=True # Procura anúncios não vistos antes
                )

                for item in anuncios:
                    # Não notifica anúncios marcados como suspeitos pelo IQR
                    if getattr(item, "is_suspeito", False):
                        continue

                    # Verifica critérios de pechincha
                    is_super = "SUPER" in (item.classificacao or "") or item.desconto_percentual >= 28.0
                    is_teto = self.preco_teto and item.preco <= self.preco_teto

                    if is_super or is_teto:
                        print(f"[Sentinela] 🎯 PECHINCHA ENCONTRADA: {item.titulo} por R$ {item.preco:.2f}")
                        self._notificar(item)

            except Exception as e:
                print(f"[Sentinela] Erro na varredura: {e}")

            # Aguarda o intervalo ou evento de parada
            segundos = self.intervalo_minutos * 60
            self.proxima_execucao = datetime.fromtimestamp(time.time() + segundos).strftime("%Y-%m-%d %H:%M:%S")
            self._stop_event.wait(timeout=segundos)

    def _notificar(self, item: Anuncio):
        alerta_info = {
            "titulo": item.titulo,
            "preco": item.preco,
            "desconto": item.desconto_percentual,
            "plataforma": item.plataforma,
            "url": item.url,
            "horario": datetime.now().strftime("%H:%M:%S")
        }
        self.ultimos_alertas.insert(0, alerta_info)
        if len(self.ultimos_alertas) > 20:
            self.ultimos_alertas.pop()
        self.total_alertas_enviados += 1

        if not self.webhook_url:
            return

        try:
            if "discord" in self.webhook_tipo:
                self._enviar_discord(item)
            elif "telegram" in self.webhook_tipo:
                self._enviar_telegram(item)
        except Exception as e:
            print(f"[Sentinela] Falha ao disparar webhook: {e}")

    def _enviar_discord(self, item: Anuncio):
        """Envia card visual rico (Embed) para Webhook do Discord."""
        embed = {
            "title": f"🔥 SUPER ACHADO: {item.titulo}",
            "url": item.url,
            "color": 0x10b981, # Verde esmeralda
            "description": f"Nova pechincha detectada pelo **Radar de Achados** no **{item.plataforma}**!",
            "fields": [
                {"name": "💰 Preço", "value": f"**R$ {item.preco:,.2f}**".replace(',', 'X').replace('.', ',').replace('X', '.'), "inline": True},
                {"name": "📉 Economia", "value": f"**{item.desconto_percentual}% abaixo** da média", "inline": True},
                {"name": "📍 Localização", "value": item.localizacao or "Não informada", "inline": True}
            ],
            "footer": {"text": "Radar de Achados • Modo Sentinela 24/7"},
            "timestamp": datetime.utcnow().isoformat()
        }

        if item.imagem_url:
            embed["thumbnail"] = {"url": item.imagem_url}

        payload = {
            "username": "Radar de Achados 🎯",
            "avatar_url": "https://img.icons8.com/fluency/96/search--v1.png",
            "embeds": [embed]
        }

        req = urllib.request.Request(
            self.webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "RadarAchadosBot/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[Sentinela Webhook] Discord notificado com status {resp.status}")

    def _enviar_telegram(self, item: Anuncio):
        """Envia mensagem formatada com botão inline para Telegram Bot API."""
        msg = (
            f"🔥 *SUPER ACHADO DETECTADO\\!*\n\n"
            f"📦 *Item:* {item.titulo}\n"
            f"💰 *Preço:* R$ {item.preco:,.2f}\n"
            f"📉 *Desconto:* {item.desconto_percentual}% abaixo do mercado\n"
            f"📍 *Local:* {item.localizacao}\n"
            f"🏷️ *Origem:* {item.plataforma}\n\n"
            f"👉 [Ver Anúncio Agora]({item.url})"
        )
        payload = {
            "chat_id": self.webhook_url.split("/")[-1] if "/" in self.webhook_url else self.webhook_url,
            "text": msg,
            "parse_mode": "Markdown"
        }
        # Webhook URL formatada para Telegram
        endpoint = self.webhook_url if "api.telegram.org" in self.webhook_url else f"https://api.telegram.org/bot{self.webhook_url}/sendMessage"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[Sentinela Webhook] Telegram notificado com status {resp.status}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "termo": self.termo,
            "uf": self.uf,
            "intervalo_minutos": self.intervalo_minutos,
            "preco_teto": self.preco_teto,
            "apenas_super_achados": self.apenas_super_achados,
            "ativo": self.ativo,
            "ultima_execucao": self.ultima_execucao,
            "proxima_execucao": self.proxima_execucao,
            "total_alertas_enviados": self.total_alertas_enviados,
            "ultimos_alertas": self.ultimos_alertas,
            "has_webhook": bool(self.webhook_url)
        }

# Instância global gerenciadora
_sentinela_global: Optional[SentinelaTask] = None

def get_sentinela_instance() -> Optional[SentinelaTask]:
    global _sentinela_global
    return _sentinela_global

def configurar_sentinela(
    termo: str,
    uf: str = "df",
    intervalo_minutos: int = 15,
    preco_teto: Optional[float] = None,
    apenas_super_achados: bool = True,
    webhook_url: Optional[str] = None,
    webhook_tipo: str = "discord"
) -> SentinelaTask:
    global _sentinela_global
    if _sentinela_global and _sentinela_global.ativo:
        _sentinela_global.stop()

    _sentinela_global = SentinelaTask(
        termo=termo,
        uf=uf,
        intervalo_minutos=intervalo_minutos,
        preco_teto=preco_teto,
        apenas_super_achados=apenas_super_achados,
        webhook_url=webhook_url,
        webhook_tipo=webhook_tipo
    )
    _sentinela_global.start()
    return _sentinela_global

def parar_sentinela():
    global _sentinela_global
    if _sentinela_global:
        _sentinela_global.stop()
        return True
    return False
