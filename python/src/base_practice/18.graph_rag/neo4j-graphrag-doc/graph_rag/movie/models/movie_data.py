# [AGC:FILE] tool=Cc author=fangkun date=2026-08-11
from typing import List, Optional
from pydantic import BaseModel


# [AGC:START] tool=Cc author=fangkun
class Movie(BaseModel):
    title: str
    released: int
    rating: float
    tagline: str
    plot_summary: str
    genres: List[str]
    keywords: Optional[List[str]] = None


class Person(BaseModel):
    name: str
    born: int
    gender: str


class Studio(BaseModel):
    name: str
    country: str


# 扩展现有 3 部电影的数据
MOVIES_DATA = [
    Movie(
        title="Inception",
        released=2010,
        rating=8.8,
        tagline="Your mind is the scene of the crime",
        plot_summary="A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a CEO.",
        genres=["Sci-Fi", "Thriller", "Action"],
        keywords=["dream", "subconscious", "heist"]
    ),
    Movie(
        title="The Dark Knight",
        released=2008,
        rating=9.0,
        tagline="Why so serious?",
        plot_summary="When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of their ability to fight injustice.",
        genres=["Action", "Crime", "Drama"],
        keywords=["superhero", "villain", "justice"]
    ),
    Movie(
        title="Interstellar",
        released=2014,
        rating=8.6,
        tagline="Mankind was born on Earth. It was never meant to die here.",
        plot_summary="A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival as Earth becomes uninhabitable.",
        genres=["Sci-Fi", "Adventure", "Drama"],
        keywords=["space", "time", "survival"]
    ),
]

PERSONS_DATA = [
    Person(name="Leonardo DiCaprio", born=1974, gender="Male"),
    Person(name="Christian Bale", born=1974, gender="Male"),
    Person(name="Matthew McConaughey", born=1969, gender="Male"),
    Person(name="Anne Hathaway", born=1982, gender="Female"),
    Person(name="Christopher Nolan", born=1970, gender="Male"),
    Person(name="Michael Caine", born=1933, gender="Male"),
]

STUDIOS_DATA = [
    Studio(name="Warner Bros.", country="USA"),
    Studio(name="Paramount Pictures", country="USA"),
    Studio(name="Legendary Pictures", country="USA"),
]
# [AGC:END]
