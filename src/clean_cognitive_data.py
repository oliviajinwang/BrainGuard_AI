import pandas as pd

LAC_COUNT_MAP = {"Zero": 0, "1 to 2": 1, "3 to 5": 2, ">5": 3}


def clean_cognitive_dataset(file_path, output_path="data/patient_view_data/cognitive_clean.csv"):
    print("Starting Cognitive & Microvascular Dataset Preprocessing Pipeline...")

    df = pd.read_csv(file_path)

    df_filtered = df[
        ["age", "gender", "educationyears", "EF", "PS", "Global", "Fazekas", "lac_count", "dementia"]
    ].copy()

    df_filtered.rename(
        columns={
            "educationyears": "education_years",
            "EF": "ef",
            "PS": "ps",
            "Global": "global_cognitive",
            "Fazekas": "fazekas",
            "dementia": "dementia_status",
        },
        inplace=True,
    )

    df_filtered["gender_male"] = (df_filtered["gender"] == "male").astype(int)
    # lac_count is reported as clinical severity bins rather than a literal
    # count -- map to an ordinal scale so the model can use it numerically.
    df_filtered["lacune_count"] = df_filtered["lac_count"].map(LAC_COUNT_MAP)
    df_filtered = df_filtered.drop(columns=["gender", "lac_count"])

    # EF/PS/Global can't be sensibly imputed -- they're the whole point of
    # this model, so rows missing any of them (or the target) are dropped
    # rather than filled with a guessed value.
    before = len(df_filtered)
    df_filtered = df_filtered.dropna(subset=["dementia_status", "ef", "ps", "global_cognitive"])
    print(f"Dropped {before - len(df_filtered)} rows missing target or cognitive scores.")

    df_filtered["dementia_status"] = df_filtered["dementia_status"].astype(int)

    print(f"Final Cleaned Shape: {df_filtered.shape[0]} rows, {df_filtered.shape[1]} columns.")
    df_filtered.to_csv(output_path, index=False)
    print(f"File successfully saved to: {output_path}")
    return df_filtered


if __name__ == "__main__":
    clean_cognitive_dataset("data/patient_view_data/OPTIMAL_combined_3studies_6feb2020 2.csv")
