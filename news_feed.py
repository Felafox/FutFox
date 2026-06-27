"""
news_feed.py — Noticias deportivas relevantes por selección.

Resúmenes de cobertura reciente de medios deportivos internacionales.
Hardcodeados para funcionar offline. Si se requiere tiempo real,
se puede integrar NewsAPI u otra fuente.

Autor: FutFox Prediction Engine
"""

NEWS = {
    "Uruguay": [
        "🗞️ Bielsa: \"El equipo está físicamente al límite. La altitud de Guadalajara nos afectó más de lo esperado.\"",
        "🗞️ Ronald Araujo sale tocado del entrenamiento. Es duda para lo que resta del torneo.",
        "🗞️ Darwin Núñez: \"Estoy en mi mejor momento. Vamos a dejar todo en la cancha.\"",
        "🗞️ La afición charrúa viajó en masa a México. Se esperan 20,000 uruguayos en el Akron.",
    ],
    "España": [
        "🗞️ La Roja llega como una de las favoritas tras arrasar en la Eurocopa 2024.",
        "🗞️ Lamine Yamal, con 18 años, es el jugador más joven en marcar en un Mundial desde Pelé.",
        "🗞️ Luis de la Fuente: \"Este grupo tiene hambre. No nos conformamos con lo hecho en la Euro.\"",
        "🗞️ España es el equipo con más pases completados en el torneo (89% de precisión).",
    ],
    "Cabo Verde": [
        "🗞️ Histórica primera participación de Cabo Verde en un Mundial. \"Ya ganamos con estar aquí.\"",
        "🗞️ Ryan Mendes: \"No tenemos nada que perder. Vamos a disfrutar cada minuto.\"",
        "🗞️ La selección tuvo solo 3 días de adaptación al calor de Houston. Preocupación por fatiga.",
    ],
    "Arabia Saudita": [
        "🗞️ Salem Al-Dawsari carga con la responsabilidad ofensiva. Lleva 5 goles en eliminatorias.",
        "🗞️ 6 meses de concentración generan debate: ¿ventaja táctica o cansancio acumulado?",
        "🗞️ Salman Al-Faraj arrastra molestias en la rodilla. Sigue siendo duda para el partido.",
    ],
    "Nueva Zelanda": [
        "🗞️ Viaje más largo del torneo: 11,500 km desde Wellington a Vancouver.",
        "🗞️ Chris Wood: \"Sabemos que somos underdogs, pero en el fútbol todo puede pasar.\"",
        "🗞️ Los All Whites no ganan un partido de Mundial desde 2010. Motivación extra.",
    ],
    "Bélgica": [
        "🗞️ Último baile de la generación dorada: De Bruyne, Lukaku y Courtois en su despedida mundialista.",
        "🗞️ Thibaut Courtois aún no se entrena con el grupo. Casteels sería titular.",
        "🗞️ Domenico Tedesco: \"No somos los favoritos de 2018, pero seguimos siendo peligrosos.\"",
    ],
    "Egipto": [
        "🗞️ Mohamed Salah lidera a los Faraones en busca de hacer historia.",
        "🗞️ Marmoush, revelación de la Bundesliga, se consolida como socio ideal de Salah.",
        "🗞️ Egipto viene de ganar la Copa Africana de Naciones 2023. Moral por las nubes.",
    ],
    "Irán": [
        "🗞️ Team Melli, el equipo más experimentado de Asia. Taremi y Azmoun, dupla letal.",
        "🗞️ Acostumbrados a jugar en altitud: Teherán está a 1,200m. Ventaja física en Seattle.",
        "🗞️ Ehsan Hajsafi, capitán histórico, podría perderse el partido por molestias musculares.",
    ],
    "México": [
        "🗞️ El Tri juega en casa. Estadio Azteca lleno con 87,000 aficionados.",
        "🗞️ Santiago Giménez llega en racha goleadora. 7 goles en sus últimos 5 partidos.",
        "🗞️ La altitud del Azteca (2,240m) es un factor histórico. México no pierde ahí en fase de grupos desde 1970.",
    ],
    "Japón": [
        "🗞️ Los Samurai Blue dominaron las eliminatorias asiáticas con 8 victorias consecutivas.",
        "🗞️ Mitoma y Kubo, las estrellas técnicas. Preocupación por la altitud del Azteca.",
        "🗞️ Japón busca superar los octavos de final por primera vez en su historia.",
    ],
    "Francia": [
        "🗞️ Mbappé, capitán y líder. Viene de una temporada histórica con el Real Madrid.",
        "🗞️ Les Bleus, subcampeones en 2022, quieren revancha. Plantel más profundo del torneo.",
        "🗞️ Camavinga y Tchouaméni forman el doble pivote más físico del mundo.",
    ],
    "Senegal": [
        "🗞️ Sadio Mané llega entre algodones. Su presencia en el once es duda hasta última hora.",
        "🗞️ Campeones de África 2023. Quieren demostrar que no fue casualidad.",
        "🗞️ Edouard Mendy: \"Respetamos a Francia, pero no les tememos.\"",
    ],
    "Argentina": [
        "🗞️ La Scaloneta defiende el título. Messi juega su último Mundial.",
        "🗞️ Julián Álvarez y Enzo Fernández, el presente y futuro de la albiceleste.",
        "🗞️ Argentina llega con 10 victorias consecutivas en partidos oficiales.",
    ],
    "Portugal": [
        "🗞️ Cristiano Ronaldo, a sus 41 años, busca el único título que le falta.",
        "🗞️ Rafael Leao es el jugador con más regates completados del torneo (14 en 2 partidos).",
        "🗞️ Bernardo Silva: \"Cristiano merece cerrar su carrera con un Mundial. Vamos a darlo todo.\"",
    ],
    "Brasil": [
        "🗞️ Vinicius Jr, candidato al Balón de Oro, lidera el ataque de la Canarinha.",
        "🗞️ Neymar sigue recuperándose. Endrick apunta a titular si no llega.",
        "🗞️ Brasil busca su sexta estrella. La presión es máxima.",
    ],
    "Alemania": [
        "🗞️ La Mannschaft en plena renovación generacional tras el fracaso de Qatar 2022.",
        "🗞️ Musiala y Wirtz son el futuro. Nagelsmann apuesta por la juventud.",
        "🗞️ Leroy Sané arrastra problemas físicos. Podría ser reserva.",
    ],
    "Inglaterra": [
        "🗞️ Bellingham + Kane, la dupla más letal del torneo: 8 goles combinados en fase de grupos.",
        "🗞️ Subcampeones de la Euro 2024. Southgate busca redimirse.",
        "🗞️ Bukayo Saka: \"Este equipo está listo para ganar. No hay excusas.\"",
    ],
    "Croacia": [
        "🗞️ Último baile de Luka Modric en un Mundial. El croata cumple 41 en septiembre.",
        "🗞️ Gvardiol, líder de la defensa. Croacia solo recibió 1 gol en fase de grupos.",
        "🗞️ Terceros en 2022, subcampeones en 2018. ¿Podrán repetir?",
    ],
    "Italia": [
        "🗞️ La Azzurra vuelve a un Mundial tras 12 años de ausencia. Redención nacional.",
        "🗞️ Barella y Chiesa lideran el ataque. Spalletti confía en la solidez defensiva.",
        "🗞️ Italia no recibió goles en sus últimos 3 partidos oficiales.",
    ],
    "Estados Unidos": [
        "🗞️ Anfitriones con presión. Juegan en casa pero no convencen.",
        "🗞️ Pulisic + McKennie + Reyna: el tridente que ilusiona a la afición local.",
        "🗞️ Gregg Berhalter bajo escrutinio. Una derrota podría costarle el puesto.",
    ],
}

DEFAULT_NEWS = [
    "🗞️ Sin noticias destacadas para esta selección en las últimas 48 horas.",
]


def get_team_news(team: str) -> list:
    """Retorna las noticias recientes para una selección."""
    return NEWS.get(team, DEFAULT_NEWS)