![hotel](./assets/hotel.jpg)

# Unterkunft Suche

Jedes Wochenende muss ich im Raum meiner Universität ein Hotelzimmer buchen, in dem ich eine Übernachtung tätigen muss.

Dieses Tool nutzt die Booking.com API um umliegende Hotels samt Preisen anzufragen und für jedes Hotel mittels Google Distance API die Fahrtzeit (Kosten) von/zur Uni zu berechnen.

## Ablauf

1. Erzeuge eine Bounding Box mit der Kantenlänge $a$ in Metern um den Ort der Uni. Das ist erstmal eine grobe Suche.
2. Nutze die [Booking.com API](https://rapidapi.com/apidojo/api/booking) um für das Übernachtungsdatum Hotels sortiert nach Preisen aufzulisten. (Auch nach Distanz ist möglich, allerdings ist die Annahme, dass Distanz bei Booking über Luftlinie berechnet wird, und nicht in Fahrtzeit o. Kosten).
3. Für jedes Hotel berechne die Fahrtzeit zu Uni
