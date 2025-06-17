# Instrukcja implementacji lokalnej aplikacji webowej (Pally)

Poniższy dokument opisuje kolejne kroki potrzebne do stworzenia prostej lokalnej aplikacji webowej w technologii **React.js** z **TypeScriptem** i **Three.js**. Aplikacja ma odwzorowywać funkcję programu Pally do układania warstw palet i działać w całości w przeglądarce bez wsparcia backendu.

## 1. Inicjalizacja projektu

1. Zainstaluj narzędzie `npm` / `yarn` i utwórz nową aplikację React z TypeScriptem np. poprzez `create-react-app` lub `Vite`:
   ```bash
   npm create vite@latest pally-webapp -- --template react-ts
   cd pally-webapp
   npm install
   ```
2. Dodaj zależności:
   ```bash
   npm install three
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p
   ```
3. Skonfiguruj pliki `tailwind.config.js` i `postcss.config.js` zgodnie z dokumentacją, aby w projekcie działał Tailwind CSS.

## 2. Model danych

1. W folderze `src` utwórz plik `models.ts`. Zdefiniuj w nim interfejsy TypeScript zgodne ze strukturą plików JSON używanych przez Pally (PPB_VERSION_NO 3.1.1). Przykładowe struktury to:
   - `PalletProject` (nazwa, opis, wymiary palety, wymiary produktu, maxGrip, guiSettings, layerTypes, layers itd.)
   - `Dimensions` (długość, szerokość, dopuszczalna wysokość ładunku, wysokość palety)
   - `ProductDimensions` (długość, szerokość, wysokość, waga)
   - `LayerType` (nazwa, klasa, pattern, altPattern, approach, altApproach)
   - `PatternItem` (x, y, r, g?, f?)

2. Zapewnij zgodność nazw pól i typów z plikiem przykładowym Pally.

## 3. Import danych z pliku JSON

1. W komponencie React stwórz przycisk **Wczytaj**. Po kliknięciu powinien otwierać okno dialogowe wyboru pliku JSON (np. poprzez element `<input type="file">`).
2. Po wybraniu pliku odczytaj go funkcją FileReader i sparsuj z użyciem `JSON.parse` do struktury `PalletProject`.
3. Sprawdź pole `guiSettings.PPB_VERSION_NO` i wyświetl ostrzeżenie, jeśli wersja jest inna niż `3.1.1`.
4. Wykonaj podstawową walidację (czy warstwy mieszczą się w obrysie palety, czy wymiary są dodatnie itp.).
5. Zapisz dane w stanie aplikacji (np. poprzez React Context lub biblioteki do zarządzania stanem).

## 4. Eksport danych do JSON

1. Stwórz przycisk **Zapisz**. Po kliknięciu aplikacja powinna zebrać aktualne ustawienia i wygenerować plik JSON zgodny z formatem Pally.
2. Upewnij się, że we wszystkich tworzonych obiektach znajduje się pole `PPB_VERSION_NO` z wartością `3.1.1` oraz pozostałe wymagane informacje.
3. Użyj obiektu `Blob` i `URL.createObjectURL`, aby użytkownik mógł pobrać wygenerowany plik na dysk.

## 5. Podstawowe komponenty aplikacji

1. **Panel ustawień palety i produktu** – formularze do wprowadzenia wymiarów i wagi, maksymalnego uchwytu itp.
2. **Lista warstw** – komponent wyświetlający kolejność warstw (elementy `layers`). Umożliwi dodawanie, usuwanie i przenoszenie warstw.
3. **Edytor warstwy** – pozwala na graficzne modyfikowanie patternu (i ewentualnie altPattern) z użyciem siatki 2D oraz podglądu 3D w Three.js.
4. **Podgląd 3D** – scena Three.js prezentująca ułożone kartony na palecie z możliwością obracania i przybliżania.

## 6. Obsługa warstw i wzorów

1. Podczas edycji warstwy użytkownik powinen móc dodawać pojedyncze kartony (elementy `PatternItem`) poprzez kliknięcie na siatkę.
2. Wprowadź logikę sprawdzającą kolizje – aby kartony nie nachodziły na siebie ani nie wychodziły poza paletę.
3. Jeśli pola `altPattern` i `altApproach` są zdefiniowane, dodaj opcje przełączania oraz automatycznego stosowania naprzemiennych warstw zgodnie z `altLayout`.

## 7. Dalsze kroki

- Rozbuduj walidację danych i możliwość cofania zmian.
- Rozważ przechowywanie stanu projektu w `localStorage`, aby użytkownik nie stracił pracy przy odświeżeniu strony.
- Dodaj przykładowe szablony warstw i możliwość wyboru gotowych rozwiązań startowych.

Dokument ma pomóc w stworzeniu prostego narzędzia lokalnego, które pozwoli użytkownikowi przeprowadzać podstawowe operacje importu, edycji i eksportu plików palety zgodnych z programem Pally.
