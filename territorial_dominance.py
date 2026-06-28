"""
territorial_dominance.py — Factor de Dominio Posicional (v3.0)

Infiere la ventaja territorial de un partido en vivo a partir de métricas
de flujo de juego, sin requerir coordenadas (X,Y) exactas.

Arquitectura:
  1. LiveMatchSignal — señales crudas desde APIs
  2. SignalNormalizer — transforma crudo → TerritorialSignal [-1, 1]
  3. DominanceBayesianUpdater — actualiza P(δ) secuencialmente
  4. LambdaDominanceAdjuster — traduce δ en ajuste de λ
  5. DominanceOutput — listo para UI

Matemática:
  δ ∈ [-1, 1]  (latente, inferido)
  λ_adj = λ_base × exp(δ × τ)
  P(δ|datos) ∝ P(δ) × Π P(señal_i|δ)

Autor: FutFox Prediction Engine
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from constants import (
    DOMINANCE_UPDATE_INTERVAL,
    PRIOR_STRENGTH_DEFAULT,
    TAU_BASE,
    TAU_RATIO,
)


# ======================================================================
# 1. Dataclasses de entrada — INGESTION HANDLER
# ======================================================================

@dataclass
class LiveMatchSignal:
    """Señales observables en un instante del partido."""
    minute: int
    score_home: int
    score_away: int
    # Señales primarias (siempre disponibles desde worldcup26.ir)
    goal_events: List[Tuple[int, str]] = field(default_factory=list)
    # Señales secundarias (opcionales, None si no disponible)
    shots_home: Optional[int] = None
    shots_away: Optional[int] = None
    shots_on_target_home: Optional[int] = None
    shots_on_target_away: Optional[int] = None
    possession_pct_home: Optional[float] = None
    passes_completed_home: Optional[int] = None
    passes_completed_away: Optional[int] = None
    corners_home: Optional[int] = None
    corners_away: Optional[int] = None


@dataclass
class TerritorialSignal:
    """Señales normalizadas a [-1, 1] listas para el motor Bayesiano."""
    minute: int
    goal_timing_pressure: float = 0.0
    score_momentum: float = 0.0
    shot_dominance: Optional[float] = None
    pass_territoriality: Optional[float] = None
    corner_pressure: Optional[float] = None
    signal_weights: Dict[str, float] = field(default_factory=dict)


# ======================================================================
# 2. Dataclasses de estado — INFERENCE ENGINE
# ======================================================================

@dataclass
class DominanceState:
    """Estado Bayesiano de δ en un instante del partido."""
    minute: int
    delta_mean: float = 0.0
    delta_variance: float = 0.25
    confidence: float = 0.0
    n_signals_processed: int = 0
    delta_timeline: List[Tuple[int, float]] = field(default_factory=list)
    interpretation: str = "Equilibrado"


# ======================================================================
# 3. Dataclasses de salida — OUTPUT
# ======================================================================

@dataclass
class DominanceOutput:
    """Datos listos para consumir por la UI."""
    state: DominanceState
    dominance_pct_home: float = 50.0
    dominance_pct_away: float = 50.0
    interpretation: str = "Equilibrado"
    heatmap_zones: Dict[str, float] = field(default_factory=dict)
    lambda_adjustment_factor_home: float = 1.0
    lambda_adjustment_factor_away: float = 1.0
    pressure_timeline: List[Dict] = field(default_factory=list)


# ======================================================================
# 4. SIGNAL NORMALIZER
# ======================================================================

class SignalNormalizer:
    """
    Convierte LiveMatchSignal → TerritorialSignal.
    Cada sub-señal se mapea a [-1, 1]:
        +1 = máxima ventaja local inferida
        −1 = máxima ventaja visitante inferida
         0 = equilibrio
    """

    def normalize(
        self,
        raw: LiveMatchSignal,
        home_strength: float,
        away_strength: float,
    ) -> TerritorialSignal:
        signal = TerritorialSignal(minute=raw.minute)
        weights = {}

        # ── Señal 1: timing de goles (siempre disponible) ──────────
        signal.goal_timing_pressure = self._normalize_goal_timing(
            raw.goal_events, raw.minute, home_strength, away_strength,
        )
        weights["goal_timing"] = 0.35

        # ── Señal 2: momentum del marcador (siempre disponible) ───
        signal.score_momentum = self._normalize_score_momentum(
            raw.score_home, raw.score_away, raw.minute,
        )
        weights["score_momentum"] = 0.25

        # ── Señal 3: dominio de tiros (opcional) ──────────────────
        if raw.shots_home is not None and raw.shots_away is not None:
            signal.shot_dominance = self._normalize_shot_dominance(raw)
            weights["shot_dominance"] = 0.20

        # ── Señal 4: territorialidad de pases (opcional) ──────────
        if raw.passes_completed_home is not None and raw.passes_completed_away is not None:
            signal.pass_territoriality = self._normalize_pass_territoriality(raw)
            weights["pass_territoriality"] = 0.10

        # ── Señal 5: presión por corners (opcional) ───────────────
        if raw.corners_home is not None and raw.corners_away is not None:
            signal.corner_pressure = self._normalize_corner_pressure(raw)
            weights["corner_pressure"] = 0.10

        # Normalizar pesos para que sumen 1
        total_w = sum(weights.values()) or 1.0
        signal.signal_weights = {k: v / total_w for k, v in weights.items()}

        return signal

    def _normalize_goal_timing(
        self,
        goal_events: List[Tuple[int, str]],
        current_minute: int,
        home_strength: float,
        away_strength: float,
    ) -> float:
        """
        Infiere presión territorial a partir del timing de goles.

        Señales:
          - Gol temprano (min < 20) → fuerte indicio de dominio
          - Respuesta rápida del rival (< 10 min después) → contesta el dominio
          - Goles tardíos del perdedor → "gol de honor", bajo peso
          - Intervalos entre goles: cortos = alta intensidad
        """
        if not goal_events or current_minute < 5:
            return 0.0

        home_goals = [(m, "home") for m, side in goal_events if side == "home"]
        away_goals = [(m, "away") for m, side in goal_events if side == "away"]

        pressure = 0.0
        n_signals = 0

        # Peso por gol temprano (decaída exponencial con el minuto)
        for minute, side in goal_events:
            early_weight = math.exp(-minute / 30.0)  # ~0.37 al min 30, ~0.05 al 90
            if side == "home":
                pressure += early_weight
            else:
                pressure -= early_weight
            n_signals += 1

        # Señal de respuesta: si un equipo marca y el otro responde rápido
        sorted_goals = sorted(goal_events, key=lambda x: x[0])
        for i in range(len(sorted_goals) - 1):
            m1, s1 = sorted_goals[i]
            m2, s2 = sorted_goals[i + 1]
            gap = m2 - m1
            if gap < 15 and s1 != s2:  # respuesta rápida del otro equipo
                response_weight = math.exp(-gap / 10.0)
                if s2 == "home":
                    pressure += response_weight * 0.5
                else:
                    pressure -= response_weight * 0.5
                n_signals += 0.5

        if n_signals == 0:
            return 0.0

        # Escalar por fuerza esperada: si el fuerte no mete goles, es señal
        # de que el débil está dominando
        expected_ratio = home_strength / max(away_strength, 0.1)
        actual_home_goals = len(home_goals)
        actual_away_goals = len(away_goals)
        if actual_home_goals + actual_away_goals > 0:
            surprise = (actual_home_goals - actual_away_goals) - math.log(expected_ratio)
            pressure += math.tanh(surprise * 0.5)

        n_signals += 1
        raw = pressure / max(n_signals, 1)
        return max(-1.0, min(1.0, raw))

    def _normalize_score_momentum(
        self, score_home: int, score_away: int, current_minute: int,
    ) -> float:
        """
        Diferencia de marcador escalada por tiempo restante.
        
        +1 → goleada local con poco tiempo (dominio confirmado)
         0 → empate
        +0.3 → ventaja mínima con mucho tiempo (aún incierto)
        """
        diff = score_home - score_away
        if diff == 0:
            return 0.0

        # Factor de tiempo: a menor tiempo restante, más peso tiene la diferencia
        remaining = max(95 - current_minute, 5)
        time_factor = 1.0 - (remaining / 95.0)  # 0 al inicio, ~1 al final
        time_factor = max(time_factor, 0.15)    # mínimo 0.15 para evitar 0

        # Diferencia escalada (1 gol = 0.5, 2 goles = 0.8, 3+ = 1.0)
        magnitude = math.tanh(abs(diff) * 0.6)
        sign = 1.0 if diff > 0 else -1.0

        return sign * magnitude * time_factor

    def _normalize_shot_dominance(self, raw: LiveMatchSignal) -> float:
        """Ratio de tiros mapeado a [-1, 1], ajustado por precisión."""
        total_shots = (raw.shots_home or 0) + (raw.shots_away or 0)
        if total_shots == 0:
            return 0.0

        raw_ratio = (raw.shots_home or 0) / total_shots

        # Ajuste por calidad: tiros al arco / tiros totales
        if raw.shots_on_target_home is not None and raw.shots_on_target_away is not None:
            sot_h = raw.shots_on_target_home or 0
            sot_a = raw.shots_on_target_away or 0
            quality_h = sot_h / max(raw.shots_home or 1, 1)
            quality_a = sot_a / max(raw.shots_away or 1, 1)
            quality_factor = (quality_h - quality_a) * 0.3
        else:
            quality_factor = 0.0

        # Mapear ratio [0, 1] → [-1, 1]
        centered = 2.0 * raw_ratio - 1.0
        return max(-1.0, min(1.0, centered + quality_factor))

    def _normalize_pass_territoriality(self, raw: LiveMatchSignal) -> float:
        """
        Diferencial de pases completados como proxy de territorialidad.
        Sin coordenadas, asumimos que más pases completados en general
        correlaciona débilmente con dominio territorial.
        """
        total = (raw.passes_completed_home or 0) + (raw.passes_completed_away or 0)
        if total == 0:
            return 0.0
        ratio = (raw.passes_completed_home or 0) / total
        # Señal débil: escala reducida (máx ±0.4)
        return (2.0 * ratio - 1.0) * 0.4

    def _normalize_corner_pressure(self, raw: LiveMatchSignal) -> float:
        """Más corners → más tiempo en área rival."""
        total = (raw.corners_home or 0) + (raw.corners_away or 0)
        if total == 0:
            return 0.0
        ratio = (raw.corners_home or 0) / total
        return (2.0 * ratio - 1.0) * 0.6


# ======================================================================
# 5. DOMINANCE BAYESIAN UPDATER
# ======================================================================

class DominanceBayesianUpdater:
    """
    Actualiza δ secuencialmente vía aproximación Bayesiana.
    
    La distribución de δ se modela como una distribución Beta
    mapeada de [0,1] → [-1,1].
    
    δ = 2 × θ − 1  donde θ ~ Beta(α, β)
    
    La actualización es un weighted pseudocount:
        α_new = α_old + Σ w_i × max(señal_i, 0)
        β_new = β_old + Σ w_i × max(−señal_i, 0)
    
    Esto preserva la interpretación: α = "evidencia de dominio local",
    β = "evidencia de dominio visitante".
    """

    def __init__(self, prior_strength: float = PRIOR_STRENGTH_DEFAULT):
        # Prior simétrica: α = β = prior_strength → δ ≈ 0
        self.alpha = prior_strength
        self.beta = prior_strength
        self._minute_last_update = 0
        self._timeline: List[Tuple[int, float]] = []

    @property
    def delta_mean(self) -> float:
        """E[δ] = 2 × E[θ] − 1 = 2 × α/(α+β) − 1"""
        total = self.alpha + self.beta
        if total == 0:
            return 0.0
        return 2.0 * (self.alpha / total) - 1.0

    @property
    def delta_variance(self) -> float:
        """Var[δ] = 4 × Var[θ] = 4 × αβ / ((α+β)²(α+β+1))"""
        total = self.alpha + self.beta
        if total <= 1:
            return 0.25
        return (4.0 * self.alpha * self.beta) / (total * total * (total + 1))

    @property
    def confidence(self) -> float:
        """
        Confianza en la estimación actual.
        Crece con el número de pseudo-observaciones.
        """
        total = self.alpha + self.beta
        if total <= 2:
            return 0.0
        return min(1.0, (total - 2) / 10.0)

    def get_likelihood(self, signal: TerritorialSignal, delta: float) -> float:
        """
        Evalúa ln P(señal | δ) para un delta candidato.
        Combina sub-likelihoods con los pesos de cada señal.
        """
        log_likelihood = 0.0
        weights = signal.signal_weights

        # Goal timing: la señal debería estar cerca de δ
        w = weights.get("goal_timing", 0.0)
        if w > 0:
            diff = signal.goal_timing_pressure - delta
            log_likelihood += w * (-0.5 * (diff ** 2) / 0.3)

        # Score momentum
        w = weights.get("score_momentum", 0.0)
        if w > 0:
            diff = signal.score_momentum - delta
            log_likelihood += w * (-0.5 * (diff ** 2) / 0.4)

        # Shot dominance
        if signal.shot_dominance is not None:
            w = weights.get("shot_dominance", 0.0)
            if w > 0:
                diff = signal.shot_dominance - delta
                log_likelihood += w * (-0.5 * (diff ** 2) / 0.25)

        # Pass territoriality (señal débil)
        if signal.pass_territoriality is not None:
            w = weights.get("pass_territoriality", 0.0)
            if w > 0:
                diff = signal.pass_territoriality - delta
                log_likelihood += w * (-0.5 * (diff ** 2) / 0.5)

        # Corner pressure
        if signal.corner_pressure is not None:
            w = weights.get("corner_pressure", 0.0)
            if w > 0:
                diff = signal.corner_pressure - delta
                log_likelihood += w * (-0.5 * (diff ** 2) / 0.35)

        return math.exp(log_likelihood)

    def update(self, signal: TerritorialSignal) -> DominanceState:
        """
        Incorpora una TerritorialSignal y actualiza α, β.
        
        Cada sub-señal contribuye como pseudo-observación:
            Si señal > 0 → evidencia de dominio local → α += |señal| × peso
            Si señal < 0 → evidencia de dominio visitante → β += |señal| × peso
        """
        w = signal.signal_weights

        # Goal timing signal
        gtp = signal.goal_timing_pressure
        wt = w.get("goal_timing", 0.0)
        if gtp > 0:
            self.alpha += gtp * wt * 2.0
        else:
            self.beta += abs(gtp) * wt * 2.0

        # Score momentum
        sm = signal.score_momentum
        ws = w.get("score_momentum", 0.0)
        if sm > 0:
            self.alpha += sm * ws * 2.0
        else:
            self.beta += abs(sm) * ws * 2.0

        # Shot dominance (opcional)
        if signal.shot_dominance is not None:
            sd = signal.shot_dominance
            wsh = w.get("shot_dominance", 0.0)
            if sd > 0:
                self.alpha += sd * wsh * 2.0
            else:
                self.beta += abs(sd) * wsh * 2.0

        # Pass territoriality (opcional)
        if signal.pass_territoriality is not None:
            pt = signal.pass_territoriality
            wp = w.get("pass_territoriality", 0.0)
            if pt > 0:
                self.alpha += pt * wp * 2.0
            else:
                self.beta += abs(pt) * wp * 2.0

        # Corner pressure (opcional)
        if signal.corner_pressure is not None:
            cp = signal.corner_pressure
            wc = w.get("corner_pressure", 0.0)
            if cp > 0:
                self.alpha += cp * wc * 2.0
            else:
                self.beta += abs(cp) * wc * 2.0

        self._minute_last_update = signal.minute
        dm = self.delta_mean
        self._timeline.append((signal.minute, dm))

        # Interpretación cualitativa
        interp = self._interpret(dm)

        return DominanceState(
            minute=signal.minute,
            delta_mean=dm,
            delta_variance=self.delta_variance,
            confidence=self.confidence,
            n_signals_processed=len(self._timeline),
            delta_timeline=list(self._timeline),
            interpretation=interp,
        )

    def _interpret(self, delta: float) -> str:
        ad = abs(delta)
        if ad < 0.15:
            return "Equilibrado"
        if ad < 0.35:
            return "Ligero dominio local" if delta > 0 else "Ligero dominio visitante"
        if ad < 0.60:
            return "Dominio local" if delta > 0 else "Dominio visitante"
        return "Asfixia local" if delta > 0 else "Asfixia visitante"


# ======================================================================
# 6. LAMBDA DOMINANCE ADJUSTER
# ======================================================================

class LambdaDominanceAdjuster:
    """
    Traduce δ → ajuste multiplicativo de λ.
    
    λ_adj = λ_base × exp(δ × τ)
    
    τ escala con la confianza: a mayor certidumbre sobre δ,
    mayor el ajuste. Esto evita sobre-reaccionar con pocos datos.
    """

    def __init__(
        self,
        tau_base: float = TAU_BASE,
        tau_ratio: float = TAU_RATIO,
    ):
        self.tau_base = tau_base
        self.tau_ratio = tau_ratio

    def adjust(
        self,
        lambda_home: float,
        lambda_away: float,
        state: DominanceState,
    ) -> Tuple[float, float]:
        delta = state.delta_mean
        tau_eff = self.tau_base * math.sqrt(state.confidence)

        if delta >= 0:
            lam_h = lambda_home * math.exp(+delta * tau_eff)
            lam_a = lambda_away * math.exp(-delta * tau_eff * self.tau_ratio)
        else:
            lam_h = lambda_home * math.exp(+delta * tau_eff * self.tau_ratio)
            lam_a = lambda_away * math.exp(-delta * tau_eff)

        return lam_h, lam_a

    def get_adjustment_factors(self, state: DominanceState) -> Tuple[float, float]:
        """Retorna los factores multiplicativos para UI."""
        delta = state.delta_mean
        tau_eff = self.tau_base * math.sqrt(state.confidence)

        if delta >= 0:
            factor_h = math.exp(+delta * tau_eff)
            factor_a = math.exp(-delta * tau_eff * self.tau_ratio)
        else:
            factor_h = math.exp(+delta * tau_eff * self.tau_ratio)
            factor_a = math.exp(-delta * tau_eff)

        return factor_h, factor_a


# ======================================================================
# 7. FUNCIÓN DE CONVENIENCIA
# ======================================================================

def compute_dominance(
    raw_signal: LiveMatchSignal,
    home_strength: float,
    away_strength: float,
    updater: Optional[DominanceBayesianUpdater] = None,
) -> Tuple[DominanceState, DominanceOutput]:
    """
    Pipeline completo de dominio posicional.
    
    Args:
        raw_signal: señales crudas del partido
        home_strength: fuerza de ataque pre-partido del local
        away_strength: fuerza de ataque pre-partido del visitante
        updater: instancia existente o None (se crea una nueva)
    
    Returns:
        DominanceState, DominanceOutput
    """
    normalizer = SignalNormalizer()
    territorial = normalizer.normalize(raw_signal, home_strength, away_strength)

    if updater is None:
        updater = DominanceBayesianUpdater()

    state = updater.update(territorial)
    adjuster = LambdaDominanceAdjuster()
    lam_h_factor, lam_a_factor = adjuster.get_adjustment_factors(state)

    dom_pct_h = (state.delta_mean + 1.0) * 50.0
    dom_pct_a = 100.0 - dom_pct_h

    output = DominanceOutput(
        state=state,
        dominance_pct_home=round(dom_pct_h, 1),
        dominance_pct_away=round(dom_pct_a, 1),
        interpretation=state.interpretation,
        lambda_adjustment_factor_home=round(lam_h_factor, 4),
        lambda_adjustment_factor_away=round(lam_a_factor, 4),
        pressure_timeline=[
            {"minute": m, "delta": round(d, 4)}
            for m, d in state.delta_timeline
        ],
    )

    return state, output


# ======================================================================
# Ejecución standalone para testing
# ======================================================================
if __name__ == "__main__":
    print("Test de territorial_dominance.py\n")

    # Simular señales: partido 1-0 al minuto 60, gol local al 35'
    raw = LiveMatchSignal(
        minute=60,
        score_home=1,
        score_away=0,
        goal_events=[(35, "home")],
        # Simular shots (opcional)
        shots_home=8, shots_away=3,
        shots_on_target_home=4, shots_on_target_away=1,
    )

    normalizer = SignalNormalizer()
    territorial = normalizer.normalize(raw, home_strength=1.5, away_strength=0.9)
    print(f"TerritorialSignal:")
    print(f"  goal_timing_pressure: {territorial.goal_timing_pressure:.3f}")
    print(f"  score_momentum: {territorial.score_momentum:.3f}")
    print(f"  shot_dominance: {territorial.shot_dominance:.3f}")
    print(f"  weights: {territorial.signal_weights}")

    updater = DominanceBayesianUpdater(prior_strength=2.0)
    state = updater.update(territorial)
    print(f"\nDominanceState:")
    print(f"  δ = {state.delta_mean:.3f} ± {math.sqrt(state.delta_variance):.3f}")
    print(f"  confidence: {state.confidence:.2f}")
    print(f"  interpretation: {state.interpretation}")

    adjuster = LambdaDominanceAdjuster(tau_base=0.5, tau_ratio=1.3)
    lam_h, lam_a = adjuster.adjust(1.8, 1.0, state)
    print(f"\nλ ajustados: H={lam_h:.3f} (orig 1.8), A={lam_a:.3f} (orig 1.0)")

    output = DominanceOutput(
        state=state,
        dominance_pct_home=round((state.delta_mean + 1.0) * 50, 1),
        dominance_pct_away=round((1.0 - state.delta_mean) * 50, 1),
        interpretation=state.interpretation,
        lambda_adjustment_factor_home=round(lam_h / 1.8, 4),
        lambda_adjustment_factor_away=round(lam_a / 1.0, 4),
    )
    print(f"\nDominanceOutput:")
    print(f"  home: {output.dominance_pct_home}% | away: {output.dominance_pct_away}%")
    print(f"  λ factor H: {output.lambda_adjustment_factor_home} | λ factor A: {output.lambda_adjustment_factor_away}")

    # Simular segunda actualización: el local mete otro gol al 70'
    raw2 = LiveMatchSignal(
        minute=70,
        score_home=2,
        score_away=0,
        goal_events=[(35, "home"), (68, "home")],
        shots_home=12, shots_away=4,
        shots_on_target_home=7, shots_on_target_away=1,
    )
    territorial2 = normalizer.normalize(raw2, 1.5, 0.9)
    state2 = updater.update(territorial2)
    lam_h2, lam_a2 = adjuster.adjust(1.8, 1.0, state2)
    print(f"\n2a actualización (2-0 al 70'):")
    print(f"  δ = {state2.delta_mean:.3f}, confidence: {state2.confidence:.2f}")
    print(f"  λ H={lam_h2:.3f}, λ A={lam_a2:.3f}")
    print(f"  interpretation: {state2.interpretation}")

    print("\n✅ Test exitoso")
