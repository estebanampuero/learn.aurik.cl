"""Catálogos de lecciones temáticas y roleplay.

Cada escenario aporta una instrucción que se inyecta al system prompt del tutor para
guiar la conversación, y una lista de OBJETIVOS visibles que el alumno debe cumplir
(checklist + barra de progreso en la UI). El examen CEFR vive en `exams.py`.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Scenario:
    id: str
    kind: str               # lesson | roleplay
    title: str              # en español (UI)
    emoji: str
    desc: str               # descripción breve para la UI
    prompt: str             # instrucción para el tutor
    objectives: list[str] = field(default_factory=list)  # metas visibles
    premium: bool = False


LESSONS = [
    Scenario("travel", "lesson", "Viajes", "✈️", "Aeropuerto, transporte y direcciones.",
             "Lección guiada sobre VIAJES: aeropuerto, transporte, pedir direcciones y reservar.",
             ["Saluda y di a dónde viajas", "Pregunta cómo llegar a un lugar",
              "Compra un boleto", "Pide ayuda con una dirección"]),
    Scenario("business", "lesson", "Negocios", "💼", "Correos, reuniones y vocabulario de oficina.",
             "Lección guiada sobre NEGOCIOS: correos, reuniones, presentaciones y oficina.",
             ["Preséntate profesionalmente", "Propón una idea en una reunión",
              "Acuerda una fecha/plazo", "Despídete formalmente"]),
    Scenario("restaurant", "lesson", "Restaurante", "🍽️", "Pedir, recomendar y pagar.",
             "Lección guiada sobre RESTAURANTE: leer la carta, pedir, preguntar y pagar.",
             ["Saluda y pide una mesa", "Ordena un plato y una bebida",
              "Pregunta por una recomendación", "Pide la cuenta y despídete"]),
    Scenario("airport", "lesson", "Aeropuerto", "🛫", "Check-in, embarque y aduana.",
             "Lección guiada sobre AEROPUERTO: check-in, embarque, seguridad y aduana.",
             ["Haz el check-in", "Pregunta por la puerta de embarque",
              "Responde en el control de seguridad", "Pregunta por tu equipaje"]),
    Scenario("university", "lesson", "Universidad", "🎓", "Clases, trámites y vida estudiantil.",
             "Lección guiada sobre UNIVERSIDAD: matrícula, clases, profesores y trámites.",
             ["Pregunta por una carrera o curso", "Pide ayuda con un trámite",
              "Habla con un profesor", "Pregunta por horarios"]),
    Scenario("daily", "lesson", "Vida cotidiana", "🏠", "Compras, rutinas y small talk.",
             "Lección guiada sobre VIDA COTIDIANA: compras, rutina, clima y conversación casual.",
             ["Saluda y habla del clima", "Cuenta tu rutina diaria",
              "Haz una compra", "Despídete con naturalidad"]),
]

ROLEPLAYS = [
    Scenario("job_interview", "roleplay", "Entrevista laboral", "🧑‍💼", "Tú postulas; el tutor entrevista.",
             "ROLEPLAY: actúa como entrevistador/a de trabajo. El alumno es el candidato. Haz preguntas "
             "reales de entrevista una a una, reacciona a sus respuestas y mantente en el papel.",
             ["Preséntate y di a qué postulas", "Describe tu experiencia",
              "Explica una fortaleza y una debilidad", "Haz una pregunta al entrevistador"]),
    Scenario("meeting", "roleplay", "Reunión de trabajo", "📊", "Discusión de proyecto en equipo.",
             "ROLEPLAY: actúa como colega en una reunión de trabajo. Discutan un proyecto, plazos y tareas.",
             ["Saluda al equipo", "Da tu opinión sobre el proyecto",
              "Propón un plazo", "Asigna o acepta una tarea"]),
    Scenario("hotel", "roleplay", "Hotel", "🏨", "Check-in, problemas y servicios.",
             "ROLEPLAY: actúa como recepcionista de hotel. El alumno es el huésped que hace check-in y pide cosas.",
             ["Haz el check-in", "Pregunta por los servicios",
              "Reporta un problema en la habitación", "Pide la hora de salida (check-out)"]),
    Scenario("doctor", "roleplay", "Médico", "🩺", "Síntomas, cita y farmacia.",
             "ROLEPLAY: actúa como médico/a. El alumno describe síntomas; haz preguntas y da indicaciones.",
             ["Describe tus síntomas", "Responde desde cuándo te sientes así",
              "Pregunta por el tratamiento", "Pregunta dónde comprar el medicamento"]),
    Scenario("berlin", "roleplay", "Viaje a Berlín", "🇩🇪", "Locales, transporte y turismo.",
             "ROLEPLAY: actúa como local en Berlín ayudando a un turista con transporte, comida y lugares.",
             ["Pregunta cómo llegar a un lugar", "Pide una recomendación de comida",
              "Compra algo en una tienda", "Agradece y despídete"]),
    Scenario("london", "roleplay", "Viaje a Londres", "🇬🇧", "Locales, transporte y turismo.",
             "ROLEPLAY: actúa como local en Londres ayudando a un turista con transporte, comida y lugares.",
             ["Pregunta cómo llegar a un lugar", "Pide una recomendación de comida",
              "Compra algo en una tienda", "Agradece y despídete"]),
    Scenario("restaurant_rp", "roleplay", "Restaurante", "🍷", "Mesero y cliente.",
             "ROLEPLAY: actúa como mesero/a en un restaurante. El alumno es el cliente que ordena.",
             ["Pide una mesa", "Ordena entrada y plato principal",
              "Pregunta por un ingrediente", "Pide la cuenta"]),
]

_ALL = {s.id: s for s in (LESSONS + ROLEPLAYS)}


def get(scenario_id: str | None) -> Scenario | None:
    return _ALL.get(scenario_id or "")


def public(s: Scenario) -> dict:
    return {"id": s.id, "kind": s.kind, "title": s.title, "emoji": s.emoji,
            "desc": s.desc, "objectives": s.objectives, "premium": s.premium}
