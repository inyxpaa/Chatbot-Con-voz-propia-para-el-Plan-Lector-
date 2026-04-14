"""
Genera un dataset de fine-tuning en formato JSONL compatible con Ray Train.
El formato utilizado es el estandar de mensajes de chat (OpenAI / HuggingFace
chat template), que Ray Train acepta directamente al usar modelos como
Llama, Mistral, etc.

Estructura de cada ejemplo:
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user",   "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}

Fuentes de datos:
  - convozpropia_chunks.txt  (web del instituto)
  - plan_lector_raw.txt      (plan lector)
  - resumenes_libros_raw.txt (libros)

El script genera pares pregunta-respuesta variados cubriendo:
  1. Preguntas sobre actividades de la web del instituto
  2. Preguntas sobre libros del plan lector (argumento, autor, personajes)
  3. Preguntas sobre el plan lector como programa educativo
  4. Preguntas generales sobre el IES Comercio y Con Voz Propia
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json
import re
import random
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
processed_dir = base_dir / "processed"
raw_dir = base_dir / "raw"
finetuning_dir = base_dir / "finetuning"
finetuning_dir.mkdir(parents=True, exist_ok=True)

output_file = finetuning_dir / "dataset_finetuning.jsonl"
output_train = finetuning_dir / "train.jsonl"
output_eval  = finetuning_dir / "eval.jsonl"

SYSTEM_PROMPT = (
    "Eres el asistente virtual del Plan Lector 'Con Voz Propia' del IES Comercio de Logroño. "
    "Tu misión es ayudar al alumnado, profesorado y familias a obtener información sobre: "
    "las actividades del plan lector, los libros recomendados por cada departamento, "
    "los autores y personajes de las obras, las actividades culturales del centro y "
    "cualquier información relacionada con el fomento de la lectura en el IES Comercio. "
    "Responde siempre en español de forma clara, precisa y adaptada al contexto educativo."
)

# ============================================================
# PLANTILLAS DE PREGUNTAS para cada tipo de contenido
# ============================================================

PREGUNTAS_LIBRO = [
    "¿De qué trata el libro '{titulo}'?",
    "¿Cuál es el argumento principal de '{titulo}'?",
    "Resume el libro '{titulo}' de {autor}.",
    "¿Quién es {autor} y qué libros ha escrito?",
    "¿Cuáles son los personajes principales de '{titulo}'?",
    "¿Por qué se trabaja '{titulo}' en el plan lector del IES Comercio?",
    "¿En qué curso se lee '{titulo}'?",
    "¿Qué actividades se hacen con el libro '{titulo}'?",
    "¿Cuál es el tema central de '{titulo}'?",
    "¿Qué tipo de libro es '{titulo}' y a qué género pertenece?",
]

PREGUNTAS_ACTIVIDAD = [
    "¿Qué actividades organiza el IES Comercio dentro del plan lector?",
    "¿Qué es la Feria del Libro del IES Comercio?",
    "¿Qué es el banco lector del IES Comercio?",
    "¿Qué actividades se hacen en la Semana de la Biblioteca?",
    "¿Qué talleres literarios ha organizado el instituto?",
    "¿En qué consiste el proyecto Con Voz Propia del IES Comercio?",
    "¿Cómo se fomenta la lectura en el IES Comercio?",
    "¿Qué concursos literarios organiza el instituto?",
    "¿Qué autores han visitado el IES Comercio?",
    "¿Qué es una tertulia dialógica?",
]

PREGUNTAS_PLAN_LECTOR = [
    "¿Cuáles son los objetivos del Plan Lector Con Voz Propia?",
    "¿Qué departamentos participan en el Plan Lector?",
    "¿Qué metodología sigue el Plan Lector del IES Comercio?",
    "¿Qué libros se leen en 1º de ESO en el IES Comercio?",
    "¿Qué libros se leen en 4º de ESO?",
    "¿Qué libros recomienda el departamento de Inglés?",
    "¿Qué libros trabaja el departamento de Filosofía?",
    "¿Qué libros se leen en Bachillerato?",
    "¿Qué libros trabaja el departamento de Geografía e Historia?",
    "¿Cuál es el libro recomendado para FP en el plan lector?",
]

# ============================================================
# DATOS CURADOS DE LIBROS para pares Q&A de calidad
# (autor, titulo, curso, resumen_breve, personajes, actividad)
# ============================================================
LIBROS_CURADOS = [
    {
        "titulo": "Drácula",
        "autor": "Bram Stoker",
        "curso": "Lengua 1º ESO",
        "genero": "Novela de terror gótica",
        "resumen": "Drácula es una novela gótica de terror escrita por Bram Stoker y publicada en 1897. Narra la historia del vampiro Conde Drácula, quien intenta trasladarse de su castillo en Transilvania a Inglaterra para encontrar nuevas víctimas. La historia está contada a través de diarios personales y cartas. El joven abogado Jonathan Harker viaja al castillo del conde y queda atrapado, dándose cuenta de que su anfitrión es un ser sobrenatural. El cazador de vampiros Abraham Van Helsing lidera la batalla contra Drácula para proteger a sus amigos.",
        "personajes": "Jonathan Harker (joven abogado), Conde Drácula (vampiro antagonista), Mina Harker (esposa de Jonathan), Lucy Westenra (amiga de Mina), Abraham Van Helsing (profesor y cazador de vampiros), Arthur Holmwood, Dr. John Seward, Quincey Morris.",
        "actividad": "Creación de un periódico y murales de personajes de terror.",
        "temas": "Terror gótico, vampirismo, el bien contra el mal, la mujer victoriana, la ciencia frente a lo sobrenatural.",
        "contexto": "Es una de las obras más influyentes de la literatura de terror universal. Creó el arquetipo moderno del vampiro. Bram Stoker era escritor y director de teatro irlandés."
    },
    {
        "titulo": "Percy Jackson y el ladrón del rayo",
        "autor": "Rick Riordan",
        "curso": "Lengua 1º ESO",
        "genero": "Novela juvenil de fantasía y mitología griega",
        "resumen": "Percy Jackson es un adolescente con dislexia e hiperactividad que descubre que es hijo de Poseidón, el dios griego del mar. Cuando el rayo maestro de Zeus desaparece, Percy es acusado del robo y debe recuperarlo para evitar una guerra entre los dioses del Olimpo. Junto a sus amigos Annabeth y Grover, emprende un viaje a través de Estados Unidos enfrentándose a criaturas mitológicas. La historia mezcla la mitología griega con la vida moderna americana de forma divertida y emocionante.",
        "personajes": "Percy Jackson (protagonista, hijo de Poseidón), Annabeth Chase (hija de Atenea, lista y estratega), Grover Underwood (sátiro y mejor amigo de Percy), Luke Castellan (traidor, hijo de Hermes), Poseidón, Zeus, Hades.",
        "actividad": "Tertulia dialógica sobre la mitología griega y sus conexiones con el mundo actual.",
        "temas": "Mitología griega, identidad y pertenencia, amistad, valentía, familia.",
        "contexto": "Rick Riordan es un autor estadounidense. Creó la saga inspirándose en la dislexia de su hijo. Es una de las sagas juveniles más vendidas del mundo."
    },
    {
        "titulo": "La ratonera",
        "autor": "Agatha Christie",
        "curso": "Lengua 2º ESO",
        "genero": "Obra de teatro de misterio",
        "resumen": "La ratonera es la obra de teatro más larga en cartelera de la historia. Un grupo de desconocidos queda atrapado por una nevada en una posada llamada Monkswell Manor. Cuando llega la policía para investigar un asesinato, descubren que el asesino podría estar entre los propios huéspedes. El suspense aumenta cuando se produce otro crimen. La inspectora investiga a cada personaje mientras todos desconfían de todos. El asombroso final es uno de los más sorprendentes de la literatura policíaca.",
        "personajes": "Mollie Ralston (propietaria de la posada), Giles Ralston (marido de Mollie), el Sargento Trotter (policía investigador), Christopher Wren (huésped excéntrico), Mrs. Boyle, Major Metcalf, Miss Casewell, Mr. Paravicini.",
        "actividad": "Cartelera literaria sobre la obra y el género policiaco.",
        "temas": "Misterio, desconfianza, secretos del pasado, identidad.",
        "contexto": "Agatha Christie es la escritora de novela policíaca más vendida de todos los tiempos. La ratonera se estrenó en Londres en 1952 y sigue en cartel. Christie creó el detective Hércules Poirot y Miss Marple."
    },
    {
        "titulo": "El diario de Ana Frank",
        "autor": "Ana Frank",
        "curso": "Lengua 3º ESO",
        "genero": "Diario autobiográfico",
        "resumen": "Ana Frank fue una niña judía que se ocultó con su familia durante dos años en un escondite secreto en Ámsterdam durante la ocupación nazi de Holanda en la Segunda Guerra Mundial. En ese escondite escribió su diario entre 1942 y 1944, describiendo su vida cotidiana, sus sueños, su desarrollo como adolescente y los horrores de la guerra. El diario termina abruptamente cuando la familia es descubierta y deportada. Ana murió en el campo de concentración de Bergen-Belsen en 1945, con sólo 15 años. Su padre Otto Frank, el único superviviente, publicó el diario.",
        "personajes": "Ana Frank (protagonista y autora), Otto Frank (padre), Edith Frank (madre), Margot Frank (hermana mayor), Peter van Pels (adolescente que también se ocultaba), Hermann y Auguste van Pels, Fritz Pfeffer.",
        "actividad": "Actividad llamada Cucaña sobre la memoria del Holocausto y los derechos humanos.",
        "temas": "Holocausto, Segunda Guerra Mundial, adolescencia, esperanza, supervivencia, antisemitismo.",
        "contexto": "Es uno de los documentos más leídos sobre el Holocausto nazi. Se ha traducido a más de 70 idiomas. La Casa de Ana Frank en Ámsterdam es un museo."
    },
    {
        "titulo": "Lazarillo de Tormes",
        "autor": "Anónimo",
        "curso": "Lengua 3º ESO",
        "genero": "Novela picaresca del Siglo de Oro español",
        "resumen": "El Lazarillo de Tormes es la primera novela picaresca española, publicada en 1554 de forma anónima. Narra en primera persona la vida de Lázaro de Tormes, un joven de familia humilde que sirve a distintos amos para sobrevivir. A través de sus aventuras con un ciego tacaño, un clérigo avaro, un escudero orgulloso y otros amos, Lázaro aprende a engañar y sobrevivir en una sociedad corrupta. La obra es una crítica satírica de la sociedad y el clero del Siglo XVI español.",
        "personajes": "Lázaro de Tormes (protagonista pícaro), El Ciego (primer amo, cruel y avaro), El Clérigo (segundo amo, más avaro aún), El Escudero (tercer amo, noble pobre y orgulloso), El Fraile, El Buldero, El Arcipreste de San Salvador.",
        "actividad": "Lectura de la obra como clásico adaptado de la literatura española.",
        "temas": "Picaresca, crítica social, hipocresía religiosa, supervivencia, ascenso social.",
        "contexto": "Fundó el género picaresco. Es obligatoria en el currículo de Lengua española. Su autor real es desconocido aunque se han propuesto varios candidatos."
    },
    {
        "titulo": "Marianela",
        "autor": "Benito Pérez Galdós",
        "curso": "Lengua 4º ESO",
        "genero": "Novela realista del siglo XIX",
        "resumen": "Marianela es una novela de Benito Pérez Galdós publicada en 1878. Narra la historia de María Canela, conocida como Nela, una joven huérfana y deforme que vive en una zona minera de España. Nela es guía del joven Pablo Penáguilas, que es ciego de nacimiento y con quien desarrolla una profunda amistad y amor. Cuando un médico logra curar la ceguera de Pablo, éste puede ver por primera vez y la realidad destruye la relación: Pablo se enamora de Florentina, una joven hermosa, y Nela no puede sobrevivir al dolor del rechazo.",
        "personajes": "María Canela 'Nela' (protagonista, huérfana y marginada), Pablo Penáguilas (joven ciego que la quiere), Florentina (prima de Pablo, bella y bondadosa), El doctor Teodoro Golfín (médico que cura a Pablo), Francisco Penáguilas (padre de Pablo).",
        "actividad": "Debate y lectura sobre temas de marginación social y la mirada del otro.",
        "temas": "Marginación social, belleza y fealdad, amor, la mirada del otro, realismo social español.",
        "contexto": "Galdós es el mayor novelista español del siglo XIX. Marianela es una de sus novelas más emotivas y breves. Trata el tema de la exclusión social con una sensibilidad única."
    },
    {
        "titulo": "Bodas de sangre",
        "autor": "Federico García Lorca",
        "curso": "Lengua 4º ESO",
        "genero": "Tragedia teatral poética",
        "resumen": "Bodas de sangre es una tragedia de Federico García Lorca estrenada en 1933, considerada una de las obras más importantes del teatro español del siglo XX. Narra la historia de una boda entre el Novio y la Novia que termina en tragedia cuando la Novia huye con Leonardo, su antiguo amor, el día de la boda. El Novio los persigue y tanto él como Leonardo mueren en una pelea. La obra mezcla prosa y poesía, y introduce elementos simbólicos como la Luna y la Muerte como personajes.",
        "personajes": "La Novia (protagonista, joven enamorada de Leonardo), El Novio, Leonardo (antiguo amor de la Novia, único con nombre propio), La Madre del Novio, La Luna (personaje simbólico), La Muerte (representada como una mendiga).",
        "actividad": "Lectura dramática del texto teatral.",
        "temas": "Amor y muerte, honor, destino trágico, pasión frente a deber, Andalucía.",
        "contexto": "García Lorca es el poeta y dramaturgo español más universal del siglo XX. Fue asesinado durante la Guerra Civil Española en 1936. La trilogía trágica incluye también Yerma y La casa de Bernarda Alba."
    },
    {
        "titulo": "Historia de una escalera",
        "autor": "Antonio Buero Vallejo",
        "curso": "Lengua 4º ESO",
        "genero": "Drama social realista",
        "resumen": "Historia de una escalera es la obra de teatro más importante de Antonio Buero Vallejo, estrenada en 1949 y ganadora del Premio Lope de Vega. Transcurre en la escalera de un edificio de vecinos de clase trabajadora en Madrid durante tres décadas: los años 20, 30 y 40. A través de tres generaciones de vecinos vemos cómo los sueños se frustran y se repiten, y cómo la pobreza y la sociedad impiden la realización personal. Los hijos terminan repitiendo los errores de sus padres.",
        "personajes": "Fernando (joven soñador), Carmina (joven de la que está enamorado Fernando), Urbano (vecino más realista y trabajador), Elvira (hija de don Manuel, enamorada de Fernando), los padres de cada personaje en los distintos actos.",
        "actividad": "Lectura dramática y análisis del teatro social de posguerra española.",
        "temas": "Frustraciones y sueños, drama social, España de posguerra, repetición generacional, clase trabajadora.",
        "contexto": "Buero Vallejo fue el dramaturgo más importante de la posguerra española. Su obra rompió con el teatro de evasión franquista para mostrar la realidad social del país."
    },
    {
        "titulo": "Maus",
        "autor": "Art Spiegelman",
        "curso": "Geografía e Historia",
        "genero": "Novela gráfica / Cómic histórico",
        "resumen": "Maus es una novela gráfica en dos volúmenes de Art Spiegelman que narra la historia de supervivencia del padre del autor durante el Holocausto nazi. Los judíos son representados como ratones y los nazis como gatos. Art entrevista a su padre Vladek, sobreviviente de Auschwitz, y reconstruye su historia. Al mismo tiempo, la obra muestra la relación tensa entre Art y su padre en el presente. En 1992 ganó el Premio Pulitzer, siendo el primer cómic en lograrlo.",
        "personajes": "Art Spiegelman (narrador, hijo), Vladek Spiegelman (padre superviviente del Holocausto), Anja (madre que murió en el Holocausto), Mala (segunda esposa de Vladek), Françoise (esposa de Art).",
        "actividad": "Tertulia dialógica sobre el Holocausto y la memoria histórica.",
        "temas": "Holocausto, memoria histórica, relación padre e hijo, trauma generacional, Segunda Guerra Mundial.",
        "contexto": "Primera novela gráfica ganadora del Premio Pulitzer. Es una de las obras fundamentales para entender el Holocausto. Forma parte del currículo de Historia en muchos países."
    },
    {
        "titulo": "Persépolis",
        "autor": "Marjane Satrapi",
        "curso": "Geografía e Historia",
        "genero": "Novela gráfica autobiográfica",
        "resumen": "Persépolis es una novela gráfica autobiográfica de Marjane Satrapi que narra su infancia y adolescencia en Irán durante la Revolución Islámica de 1979 y la guerra Irán-Irak. Marji crece en una familia laica y progresista que ve cómo el país se transforma en una república islámica. Ella sufre la represión, la guerra y las restricciones a las mujeres antes de ser enviada a Europa para estudiar. La obra es un relato íntimo y político sobre la identidad, el exilio y la resistencia.",
        "personajes": "Marji / Marjane (protagonista y narradora), los padres de Marjane (progresistas e ilustrados), la abuela (fuente de sabiduría y valores), el tío Anoosh (héroe familiar ejecutado por el régimen).",
        "actividad": "Tertulia dialógica sobre derechos humanos, feminismo y libertad.",
        "temas": "Revolución iraní, feminismo, identidad cultural, exilio, resistencia política, adolescencia.",
        "contexto": "Marjane Satrapi es una autora iraní afincada en Francia. Persépolis fue adaptada al cine de animación en 2007. Es una obra fundamental para comprender el mundo islámico contemporáneo."
    },
    {
        "titulo": "El Principito",
        "autor": "Antoine de Saint-Exupéry",
        "curso": "Filosofía 1º Bachillerato y 1º ESO",
        "genero": "Fábula filosófica y poética",
        "resumen": "El Principito es un relato corto publicado en 1943 por el escritor y aviador francés Antoine de Saint-Exupéry. Un aviador que queda varado en el desierto del Sahara conoce a un pequeño príncipe llegado del asteroide B-612. El principito le cuenta sus viajes por distintos planetas donde conoció personajes absurdos que representan defectos humanos: el vanidoso, el borracho, el hombre de negocios... En la Tierra, el principito aprende sobre el amor y la amistad gracias a una rosa y un zorro. La frase más famosa es: 'Lo esencial es invisible a los ojos'.",
        "personajes": "El Principito (niño del asteroide B-612, puro e inocente), El Aviador (narrador, adulto que lo entiende), La Rosa (el amor del principito, orgullosa y dependiente), El Zorro (que le enseña a domesticar y la responsabilidad), El Rey, el Vanidoso, el Bebedor, el Hombre de Negocios, el Farolero, el Geógrafo.",
        "actividad": "Análisis y comentario por grupos y parejas. Reflexión filosófica.",
        "temas": "Amistad y responsabilidad, infancia vs. adultez, lo esencial e invisible, el amor, la soledad, la pérdida.",
        "contexto": "Es el libro más traducido de la historia después de la Biblia. Saint-Exupéry murió en misión de vuelo en 1944. Aunque parece un libro para niños, es una profunda obra filosófica para adultos."
    },
    {
        "titulo": "¿Quién se ha llevado mi queso?",
        "autor": "Spencer Johnson",
        "curso": "Comercio y Márketing 1ACO",
        "genero": "Parábola empresarial / Autoayuda",
        "resumen": "¿Quién se ha llevado mi queso? es una parábola empresarial de Spencer Johnson publicada en 1998. Cuenta la historia de cuatro personajes: dos ratones llamados Fisgón y Escurridizo, y dos humanos en miniatura llamados Hem y Haw, que viven en un laberinto y buscan queso, que simboliza la felicidad y el éxito. Cuando el queso desaparece, cada personaje reacciona de manera diferente: los ratones se adaptan rápido, Hem se niega a cambiar y Haw aprende que debe adaptarse al cambio. El libro enseña a manejar el cambio en el trabajo y la vida.",
        "personajes": "Fisgón (ratón que actúa de inmediato), Escurridizo (ratón que huye del problema), Hem (humano que se niega al cambio), Haw (humano que aprende a adaptarse).",
        "actividad": "Lectura en clase, reflexión y aplicación a los contenidos del módulo de Comercio.",
        "temas": "Gestión del cambio, adaptabilidad, trabajo en equipo, actitud ante los problemas, empresa y liderazgo.",
        "contexto": "Es uno de los libros de negocios más vendidos del mundo. Muy utilizado en el mundo empresarial y en formación profesional para enseñar gestión del cambio."
    },
    {
        "titulo": "The Great Gatsby",
        "autor": "F. Scott Fitzgerald",
        "curso": "Inglés 1º Bachillerato",
        "genero": "Novela de la época del jazz americana",
        "resumen": "El Gran Gatsby es una novela ambientada en Nueva York en los años 20, durante los llamados Felices Años Veinte. El narrador Nick Carraway se muda junto a la lujosa mansión de Jay Gatsby, un misterioso millonario que organiza fiestas fastuosas. Nick descubre que Gatsby está obsesionado con recuperar el amor de Daisy Buchanan, su antigua novia ahora casada. La novela critica el Sueño Americano, la superficialidad de los ricos y cómo el dinero no garantiza la felicidad ni el amor.",
        "personajes": "Jay Gatsby (protagonista, millonario misterioso y romántico), Nick Carraway (narrador, primo de Daisy), Daisy Buchanan (el amor de Gatsby, fría y superficial), Tom Buchanan (marido de Daisy, arrogante), Jordan Baker (amiga de Daisy), Myrtle Wilson.",
        "actividad": "Lectura adaptada con resumen, preguntas de comprensión y reflexión final.",
        "temas": "El Sueño Americano y su fracaso, desigualdad social, amor y obsesión, apariencia vs. realidad, los Felices Años Veinte.",
        "contexto": "F. Scott Fitzgerald es el cronista por excelencia de la Generación Perdida americana. La novela fue un fracaso de ventas en su época y se convirtió en obra maestra póstumamente. Ha sido adaptada al cine varias veces."
    },
    {
        "titulo": "The Adventures of Tom Sawyer",
        "autor": "Mark Twain",
        "curso": "Inglés 1º ESO",
        "genero": "Novela de aventuras juvenil americana",
        "resumen": "Las Aventuras de Tom Sawyer es una novela de Mark Twain publicada en 1876. Narra las travesuras de Tom Sawyer, un niño huérfano criado por su tía Polly en el pueblo ficticio de St. Petersburg, a orillas del río Mississippi. Tom y su amigo Huckleberry Finn son testigos accidentales de un asesinato cometido por el malvado Injun Joe. Tras muchas aventuras, Tom y Becky quedan perdidos en una cueva donde se encuentran con Injun Joe, logrando escapar y encontrar un tesoro.",
        "personajes": "Tom Sawyer (protagonista, travieso e imaginativo), Huckleberry Finn (mejor amigo, hijo de un borracho), Becky Thatcher (amor de Tom), Injun Joe (villano asesino), La tía Polly (tía que cuida a Tom), Jim (amigo esclavo), The Widow Douglas.",
        "actividad": "Lectura adaptada en voz alta con booklet de ilustraciones y actividades de comprensión.",
        "temas": "Aventura y amistad, infancia y libertad, justicia y cobardía, vida en el Mississippi del siglo XIX.",
        "contexto": "Mark Twain es considerado el padre de la literatura americana moderna. Tom Sawyer dio lugar a la secuela Huckleberry Finn. La novela es un retrato nostálgico de la infancia americana."
    },
    {
        "titulo": "Endurance, la prisión blanca",
        "autor": "Alfred Lansing",
        "curso": "Geografía e Historia",
        "genero": "Relato de aventuras / Non-fiction",
        "resumen": "Endurance narra la expedición antártica de Ernest Shackleton entre 1914 y 1916. El barco Endurance quedó atrapado en el hielo del mar de Weddell y fue destruido por la presión del hielo. Shackleton y sus 27 hombres sobrevivieron meses a la deriva sobre el hielo y luego navegaron 1.300 km en botes salvavidas hasta la isla Elefante. Shackleton cruzó a pie la isla de Georgia del Sur para pedir rescate. Ningún miembro de la expedición murió. Es considerada una de las mayores historias de supervivencia de la historia.",
        "personajes": "Ernest Shackleton (líder de la expedición), Frank Wild (segundo al mando), Frank Worsley (capitán del Endurance), Tom Crean, el fotógrafo Frank Hurley (documentó la expedición).",
        "actividad": "Tertulia dialógica sobre liderazgo, supervivencia y trabajo en equipo.",
        "temas": "Supervivencia extrema, liderazgo, trabajo en equipo, la naturaleza como adversario, la exploración polar.",
        "contexto": "Alfred Lansing escribió el libro en 1959 basándose en diarios y entrevistas a supervivientes. Las fotografías originales de Hurley son una joya documental. La historia de Shackleton se estudia en escuelas de liderazgo de todo el mundo."
    },
]

# ============================================================
# CARGAR CHUNKS DEL DATALAKE
# ============================================================

def cargar_chunks(path: Path) -> list[str]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        texto = f.read()
    return [c.strip() for c in texto.split("\n---\n") if c.strip() and len(c.strip()) > 30]


# ============================================================
# GENERADORES DE PARES Q&A
# ============================================================

def crear_ejemplo(pregunta: str, respuesta: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": pregunta},
            {"role": "assistant", "content": respuesta},
        ]
    }


def generar_ejemplos_libros(libros: list[dict]) -> list[dict]:
    ejemplos = []
    for libro in libros:
        t = libro["titulo"]
        a = libro["autor"]
        c = libro["curso"]

        # Argumento
        ejemplos.append(crear_ejemplo(
            f"¿De qué trata el libro '{t}'?",
            f"'{t}' de {a} es una obra de {libro['genero']}. {libro['resumen']}"
        ))
        ejemplos.append(crear_ejemplo(
            f"Resume el libro '{t}'.",
            libro["resumen"]
        ))
        # Personajes
        ejemplos.append(crear_ejemplo(
            f"¿Cuáles son los personajes principales de '{t}'?",
            f"Los personajes principales de '{t}' son: {libro['personajes']}"
        ))
        # Autor
        ejemplos.append(crear_ejemplo(
            f"¿Quién es {a}, el autor de '{t}'?",
            f"{a} es el autor de '{t}'. {libro['contexto']}"
        ))
        # Temas
        ejemplos.append(crear_ejemplo(
            f"¿Cuáles son los temas principales de '{t}'?",
            f"Los temas principales de '{t}' son: {libro['temas']}."
        ))
        # Actividad
        ejemplos.append(crear_ejemplo(
            f"¿Qué actividades se realizan con el libro '{t}' en el IES Comercio?",
            f"En el IES Comercio, el libro '{t}' se trabaja en {c}. La actividad principal es: {libro['actividad']}"
        ))
        # Curso
        ejemplos.append(crear_ejemplo(
            f"¿En qué curso se lee '{t}' en el IES Comercio?",
            f"'{t}' de {a} se lee en {c} del IES Comercio."
        ))
        # Contexto
        ejemplos.append(crear_ejemplo(
            f"¿Qué contexto histórico o literario tiene la obra '{t}'?",
            f"Sobre '{t}': {libro['contexto']}"
        ))

    return ejemplos


def generar_ejemplos_plan_lector() -> list[dict]:
    return [
        crear_ejemplo(
            "¿Qué es el Plan Lector Con Voz Propia del IES Comercio?",
            "El Plan Lector 'Con Voz Propia' es un proyecto de innovación educativa (PIE) del IES Comercio de Logroño diseñado para fomentar la lectura entre el alumnado de todos los cursos y departamentos. Integra la lectura como eje transversal en todas las materias e implica a toda la comunidad educativa."
        ),
        crear_ejemplo(
            "¿Cuáles son los objetivos del Plan Lector Con Voz Propia?",
            "Los objetivos del Plan Lector son: mejorar la competencia en comunicación lingüística, prevenir el abandono escolar, fomentar la lectura entre el alumnado, impulsar el trabajo colaborativo, desarrollar la sensibilidad artística, colaborar con agentes externos como la Biblioteca Rafael Azcona, promover la creatividad literaria, fomentar el diálogo y la expresión oral, dinamizar la biblioteca del centro e integrar la competencia lectora en todas las materias."
        ),
        crear_ejemplo(
            "¿Qué departamentos participan en el Plan Lector del IES Comercio?",
            "En el Plan Lector del IES Comercio participan los departamentos de: Lengua, Orientación, Biología y Geología, Ciencias de la Tierra, Administrativo, Informática y Comunicaciones, Comercio y Márketing, Geografía e Historia, Educación Física, Filosofía, Educación Plástica e Inglés."
        ),
        crear_ejemplo(
            "¿Qué libros se leen en 1º de ESO en el IES Comercio?",
            "En 1º de ESO se leen en el área de Lengua: Drácula de Bram Stoker (con actividad de periódico y murales de terror), Percy Jackson y el ladrón del rayo de Rick Riordan (con tertulia dialógica) y Ausencias de Ramón Rodríguez y Cristina Bueno (con creación de un cómic). En Inglés se lee The Adventures of Tom Sawyer de Mark Twain. En Educación Física se trabajan cuentos de valores y en Filosofía El Principito de Antoine de Saint-Exupéry."
        ),
        crear_ejemplo(
            "¿Qué libros se leen en 4º de ESO en el IES Comercio?",
            "En 4º de ESO se leen en Lengua: Marianela de Benito Pérez Galdós, Donde surgen las sombras de David Lozano, Bodas de sangre de Federico García Lorca, Caperucita en Manhattan de Carmen Martín Gaite, Historia de una escalera de Antonio Buero Vallejo y La mecánica del corazón de Mathías Malzieu. En Inglés se lee The Secret of the Lake y en Geografía e Historia se trabajan Maus, Persépolis, Endurance y Siete historias para la infanta Margarita."
        ),
        crear_ejemplo(
            "¿Qué libros recomienda el departamento de Inglés?",
            "El departamento de Inglés recomienda: The Adventures of Tom Sawyer de Mark Twain para 1º ESO, The Murders in the Rue Morgue y The Indian in the Cupboard para 2º ESO, Smile de Raina Telgemeier para 3º ESO, The Secret of the Lake para 4º ESO y The Great Gatsby de F. Scott Fitzgerald para 1º de Bachillerato."
        ),
        crear_ejemplo(
            "¿Qué es el banco lector del IES Comercio?",
            "El banco lector es un espacio del hall del IES Comercio decorado con motivos literarios donde el alumnado expone sus trabajos relacionados con la lectura. Los alumnos de distintos grupos decoran el banco lector en fechas señaladas como el Día de la Paz, el Día de la Mujer, el Día de la Poesía o el Día de la Biblioteca, acompañando las decoraciones con investigaciones y reflexiones sobre los temas trabajados."
        ),
        crear_ejemplo(
            "¿Qué es una tertulia dialógica en el contexto del plan lector?",
            "Una tertulia dialógica es una metodología de aprendizaje dialógico en la que el alumnado lee previamente fragmentos de un libro y luego, en clase, comparte los fragmentos que más les han impactado, argumentando y dialogando sobre ellos. Se basa en el respeto al turno de palabra, la escucha activa y la construcción colectiva del conocimiento. El IES Comercio la utiliza con obras como Maus, Persépolis, Endurance, Percy Jackson y otras."
        ),
        crear_ejemplo(
            "¿Qué actividades culturales organiza el IES Comercio relacionadas con la lectura?",
            "El IES Comercio organiza diversas actividades culturales: Feria del Libro (intercambio de libros en los recreos), Semana de la Biblioteca, concurso de Relatos de Terror en Noviembre Literario, concurso de Calendario de Adviento de Citas Célebres, Escape Room literario, decoración del banco lector por fechas especiales, encuentros con autores como Manu Carbajo, Marina Casado y Mikel Chasco, visitas a la Biblioteca Rafael Azcona y salidas culturales como la ruta machadiana a Soria."
        ),
        crear_ejemplo(
            "¿Qué es el proyecto 'Tirar de la Lengua' del IES Comercio?",
            "Tirar de la Lengua es el Plan de Innovación Educativa (PIE) del IES Comercio relacionado con la lectura y el lenguaje. Es el programa marco dentro del cual se desarrollan las actividades del Plan Lector y otros proyectos interdisciplinares que fomentan la lectura, la escritura y la expresión oral en todas las materias del centro."
        ),
        crear_ejemplo(
            "¿Qué es la Biblioteca Rafael Azcona y qué relación tiene con el IES Comercio?",
            "La Biblioteca Rafael Azcona es una biblioteca pública de Logroño con la que el IES Comercio colabora habitualmente en actividades del Plan Lector. El instituto realiza visitas con distintos grupos de alumnos para participar en talleres, presentaciones de libros y encuentros con autores. Allí se han realizado actividades como la visita al espectáculo de Las mil y una noches con el narrador Héctor Urién, el taller de ilustración sobre Machado y encuentros con escritores."
        ),
    ]


def generar_ejemplos_desde_chunks(chunks: list[str], num_ejemplos: int = 80) -> list[dict]:
    """Genera pares Q&A a partir de chunks del datalake de la web."""
    ejemplos = []
    chunks_web = [c for c in chunks if "iescomercio" in c.lower() or "actividad" in c.lower()]
    muestra = random.sample(chunks_web, min(num_ejemplos, len(chunks_web)))

    plantillas_q = [
        "¿Qué información tienes sobre esto: {contenido_breve}?",
        "Cuéntame más sobre la siguiente actividad del IES Comercio: {contenido_breve}.",
        "¿Puedes explicar qué es {contenido_breve} en el IES Comercio?",
    ]

    for chunk in muestra:
        # Extraer info del chunk
        lineas = chunk.split('\n')
        texto_contenido = " ".join(
            l for l in lineas
            if not l.startswith('[FUENTE') and not l.startswith('[URL')
        ).strip()

        if len(texto_contenido) < 40:
            continue

        # Primera frase como gancho
        primera_frase = re.split(r'\.\s', texto_contenido)[0][:120]

        pregunta = random.choice(plantillas_q).format(contenido_breve=primera_frase)
        respuesta = texto_contenido[:800]

        ejemplos.append(crear_ejemplo(pregunta, respuesta))

    return ejemplos


# ============================================================
# EJECUCION PRINCIPAL
# ============================================================

print("Cargando datos del datalake...")
chunks = cargar_chunks(processed_dir / "convozpropia_chunks.txt")
print(f"  Chunks cargados: {len(chunks)}")

print("\nGenerando ejemplos de fine-tuning...")
todos_los_ejemplos = []

# 1. Ejemplos de libros curados con alta calidad
ejemplos_libros = generar_ejemplos_libros(LIBROS_CURADOS)
print(f"  Ejemplos de libros: {len(ejemplos_libros)}")
todos_los_ejemplos.extend(ejemplos_libros)

# 2. Ejemplos del plan lector
ejemplos_plan = generar_ejemplos_plan_lector()
print(f"  Ejemplos del plan lector: {len(ejemplos_plan)}")
todos_los_ejemplos.extend(ejemplos_plan)

# 3. Ejemplos generados desde chunks de la web
ejemplos_chunks = generar_ejemplos_desde_chunks(chunks, num_ejemplos=100)
print(f"  Ejemplos desde chunks del datalake: {len(ejemplos_chunks)}")
todos_los_ejemplos.extend(ejemplos_chunks)

# Mezclar aleatoriamente
random.seed(42)
random.shuffle(todos_los_ejemplos)

# ---- Split train/eval (90% / 10%) ----
split_idx = int(len(todos_los_ejemplos) * 0.9)
train_set = todos_los_ejemplos[:split_idx]
eval_set  = todos_los_ejemplos[split_idx:]

# ---- Guardar todo el dataset y splits ----
def guardar_jsonl(data: list[dict], path: Path):
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"  Guardado: {path} ({len(data)} ejemplos)")

guardar_jsonl(todos_los_ejemplos, output_file)
guardar_jsonl(train_set, output_train)
guardar_jsonl(eval_set, output_eval)

# ---- Escribir README del dataset ----
readme = finetuning_dir / "README.md"
with open(readme, "w", encoding="utf-8") as f:
    f.write(f"""# Dataset de Fine-Tuning — Plan Lector Con Voz Propia

## Descripcion
Dataset generado para fine-tuning supervisado (SFT) del chatbot del IES Comercio.

## Estadisticas
- **Total de ejemplos:** {len(todos_los_ejemplos)}
- **Train:** {len(train_set)} ejemplos
- **Eval:** {len(eval_set)} ejemplos

## Formato
Cada linea del fichero JSONL contiene un objeto con la estructura de mensajes de chat:

```json
{{
  "messages": [
    {{"role": "system", "content": "..."}},
    {{"role": "user",   "content": "..."}},
    {{"role": "assistant", "content": "..."}}
  ]
}}
```

## Ficheros
- `dataset_finetuning.jsonl` — Dataset completo
- `train.jsonl` — 90% para entrenamiento
- `eval.jsonl`  — 10% para evaluacion

## Uso con Ray Train

```python
import ray
from ray.train.huggingface import TransformersTrainer
from datasets import load_dataset

ds_train = load_dataset("json", data_files="train.jsonl", split="train")
ds_eval  = load_dataset("json", data_files="eval.jsonl",  split="train")
```

## Categorias de ejemplos
1. **Libros del Plan Lector** — argumento, personajes, autor, temas, actividades ({len(ejemplos_libros)})
2. **Plan Lector** — objetivos, metodologia, departamentos, actividades ({len(ejemplos_plan)})
3. **Web del instituto** — actividades, concursos y eventos ({len(ejemplos_chunks)})
""")

print(f"\nDataset de fine-tuning completado.")
print(f"  Total ejemplos: {len(todos_los_ejemplos)}")
print(f"  Train: {len(train_set)}  |  Eval: {len(eval_set)}")
print(f"  Directorio: {finetuning_dir}")
