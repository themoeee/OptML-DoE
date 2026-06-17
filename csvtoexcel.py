from pathlib import Path
import pandas as pd

INPUT_FILES = [
    "results.csv",
    "all_results.csv",
]


def csv_to_excel(csv_path: Path):
    if not csv_path.exists():
        print(f"Skipped: {csv_path} not found")
        return

    xlsx_path = csv_path.with_name(csv_path.stem + "_clean.xlsx")

    df = pd.read_csv(csv_path)
    df.columns = [col.strip() for col in df.columns]

    # Datum sauber formatieren
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Numerische Spalten sauber machen
    numeric_cols = [
        "x1", "y1", "x2", "y2", "x3", "y3",
        "angle", "energy_objective", "stress_constraint"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")


    # Sortieren: beste energy nach oben
    sort_cols = []
    ascending = []

    if "feasible" in df.columns:
        sort_cols.append("feasible")
        ascending.append(False)

    if "energy_objective" in df.columns:
        sort_cols.append("energy_objective")
        ascending.append(False)

    if sort_cols:
        df = df.sort_values(sort_cols, ascending=ascending)

    # Bestes Sample markieren
    df["best_in_file"] = False
    if len(df) > 0:
        df.loc[df.index[0], "best_in_file"] = True

    # Excel schreiben
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Results", index=False)

        ws = writer.book["Results"]

        # Header fixieren
        ws.freeze_panes = "A2"

        # Filter aktivieren
        ws.auto_filter.ref = ws.dimensions

        # Spaltenbreite anpassen
        for column_cells in ws.columns:
            max_length = 0
            column_letter = column_cells[0].column_letter

            for cell in column_cells:
                if cell.value is not None:
                    max_length = max(max_length, len(str(cell.value)))

            ws.column_dimensions[column_letter].width = min(max_length + 2, 25)

        # Zahlenformate
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                header = ws.cell(row=1, column=cell.column).value

                if header in ["x1", "y1", "x2", "y2", "x3", "y3", "angle"]:
                    cell.number_format = "0.000"

                elif header in ["energy_objective", "stress_constraint"]:
                    cell.number_format = "0.00"

                elif header == "date":
                    cell.number_format = "yyyy-mm-dd hh:mm:ss"

    print(f"Saved: {xlsx_path}")


def main():
    for filename in INPUT_FILES:
        csv_to_excel(Path(filename))


if __name__ == "__main__":
    main()