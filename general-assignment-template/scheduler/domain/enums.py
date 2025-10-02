from enum import IntEnum

class Rating(IntEnum):
    DONT_REMEMBER = 0 
    REMEMBERED = 1     
    INSTANT = 2       

RATING_LABELS = {
    Rating.DONT_REMEMBER: "分からない",
    Rating.REMEMBERED: "分かる",
    Rating.INSTANT: "簡単",
}