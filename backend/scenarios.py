"""Catálogos de lecciones temáticas, roleplay y modo examen.

Cada escenario aporta una instrucción que se inyecta al system prompt del tutor para
guiar la conversación. Son comunes a ambos idiomas (el idioma objetivo lo fija el tutor).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    id: str
    kind: str          # lesson | roleplay | exam
    title: str         # en español (UI)
    emoji: str
    desc: str          # descripción breve para la UI
    prompt: str        # instrucción para el tutor


LESSONS = [
    Scenario("travel", "lesson", "Viajes", "✈️", "Aeropuerto, transporte y direcciones.",
             "Lección guiada sobre VIAJES: aeropuerto, transporte, pedir direcciones y reservar."),
    Scenario("business", "lesson", "Negocios", "💼", "Correos, reuniones y vocabulario de oficina.",
             "Lección guiada sobre NEGOCIOS: correos, reuniones, presentaciones y oficina."),
    Scenario("restaurant", "lesson", "Restaurante", "🍽️", "Pedir, recomendar y pagar.",
             "Lección guiada sobre RESTAURANTE: leer la carta, pedir, preguntar y pagar."),
    Scenario("airport", "lesson", "Aeropuerto", "🛫", "Check-in, embarque y aduana.",
             "Lección guiada sobre AEROPUERTO: check-in, embarque, seguridad y aduana."),
    Scenario("university", "lesson", "Universidad", "🎓", "Clases, trámites y vida estudiantil.",
             "Lección guiada sobre UNIVERSIDAD: matrícula, clases, profesores y trámites."),
    Scenario("daily", "lesson", "Vida cotidiana", "🏠", "Compras, rutinas y small talk.",
             "Lección guiada sobre VIDA COTIDIANA: compras, rutina, clima y conversación casual."),
]

ROLEPLAYS = [
    Scenario("job_interview", "roleplay", "Entrevista laboral", "🧑‍💼", "Tú postulas; el tutor entrevista.",
             "ROLEPLAY: actúa como entrevistador/a de trabajo. El alumno es el candidato. Haz preguntas "
             "reales de entrevista una a una, reacciona a sus respuestas y mantente en el papel."),
    Scenario("meeting", "roleplay", "Reunión de trabajo", "📊", "Discusión de proyecto en equipo.",
             "ROLEPLAY: actúa como colega en una reunión de trabajo. Discutan un proyecto, plazos y tareas."),
    Scenario("hotel", "roleplay", "Hotel", "🏨", "Check-in, problemas y servicios.",
             "ROLEPLAY: actúa como recepcionista de hotel. El alumno es el huésped que hace check-in y pide cosas."),
    Scenario("doctor", "roleplay", "Médico", "🩺", "Síntomas, cita y farmacia.",
             "ROLEPLAY: actúa como médico/a. El alumno describe síntomas; haz preguntas y da indicaciones."),
    Scenario("berlin", "roleplay", "Viaje a Berlín", "🇩🇪", "Locales, transporte y turismo.",
             "ROLEPLAY: actúa como local en Berlín ayudando a un turista con transporte, comida y lugares."),
    Scenario("london", "roleplay", "Viaje a Londres", "🇬🇧", "Locales, transporte y turismo.",
             "ROLEPLAY: actúa como local en Londres ayudando a un turista con transporte, comida y lugares."),
    Scenario("restaurant_rp", "roleplay", "Restaurante", "🍷", "Mesero y cliente.",
             "ROLEPLAY: actúa como mesero/a en un restaurante. El alumno es el cliente que ordena."),
]

EXAMS = [
    Scenario("goethe", "exam", "Goethe (alemán)", "🇩🇪", "Práctica estilo examen Goethe.",
             "MODO EXAMEN Goethe (alemán): simula tareas del examen (Sprechen/Schreiben), evalúa con rúbrica "
             "y da feedback de nivel. Mantén el rigor de un examinador."),
    Scenario("ielts", "exam", "IELTS", "🇬🇧", "Speaking/Writing estilo IELTS.",
             "MODO EXAMEN IELTS: simula tareas de Speaking/Writing, puntúa por bandas y da feedback."),
    Scenario("toefl", "exam", "TOEFL", "🦅", "Tareas integradas estilo TOEFL.",
             "MODO EXAMEN TOEFL: simula tareas integradas, evalúa y da feedback con criterios TOEFL."),
    Scenario("cambridge", "exam", "Cambridge", "🎓", "First/Advanced estilo Cambridge.",
             "MODO EXAMEN Cambridge (First/Advanced): simula tareas, evalúa con criterios Cambridge."),
]

_ALL = {s.id: s for s in (LESSONS + ROLEPLAYS + EXAMS)}


def get(scenario_id: str | None) -> Scenario | None:
    return _ALL.get(scenario_id or "")


def public(s: Scenario) -> dict:
    return {"id": s.id, "kind": s.kind, "title": s.title, "emoji": s.emoji, "desc": s.desc}


def by_kind(kind: str) -> list[Scenario]:
    return {"lesson": LESSONS, "roleplay": ROLEPLAYS, "exam": EXAMS}.get(kind, [])
