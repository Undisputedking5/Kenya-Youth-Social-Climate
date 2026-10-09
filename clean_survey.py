"""Clean the Kenyan Youth Social Climate responses and rename columns to short names.
Usage: python clean_survey.py responses.xlsx   (also accepts .csv)
Writes survey_clean.csv and survey_platforms.csv next to the input.
"""
import sys, re
import pandas as pd

path = sys.argv[1]
df = pd.read_csv(path) if path.endswith(".csv") else pd.read_excel(path)

# ---- 1. Rename columns by POSITION (Google's long names are messy) ----
# Positions match the CURRENT form (43 questions + timestamp). Update if the form changes.
names = (
    ["timestamp", "age_group", "gender", "region", "education", "grew_up_area",
     "social_media_time", "platforms", "see_gender_conflict_content", "see_social_issue_content"]
    + [f"q{n}_gender" for n in range(10, 16)]            # Q10-15
    + [f"q{n}_econ_class" for n in range(16, 25)]        # Q16-24
    + ["bullied_personally", "witnessed_bullying", "bullying_frequency",
       "bullying_location", "bullying_seriousness", "cyberbullying_important",  # Q25-30
       "western_asian_media_freq",                        # Q31+Q32 merged in the form
       "intl_media_success", "intl_media_identity",       # Q34, Q35 (Q33 is missing in the form)
       "culture_blending"]                                # Q36
    + [f"q{n}_trust" for n in range(37, 44)]             # Q37-43
    + ["biggest_challenge", "reduce_division"]            # Q44-45
)
assert len(names) == df.shape[1], f"expected {len(names)} columns, file has {df.shape[1]}"
df.columns = names

# ---- 2. Standardise text (case, spaces, spelling) ----
text_cols = df.select_dtypes(exclude="number").columns.drop("timestamp").difference(["biggest_challenge", "reduce_division"])
for c in text_cols:
    df[c] = (df[c].astype("string").str.strip().str.lower()
             .str.replace("influencial", "influential", regex=False)
             .str.replace(r"neither (dis)?agree (or|nor) (dis)?agree", "neither agree nor disagree", regex=True)
             .str.replace("neighborhood", "neighbourhood", regex=False)
             .str.replace("–", "-", regex=False))
for c in ["biggest_challenge", "reduce_division"]:
    df[c] = df[c].astype("string").str.strip().replace("", pd.NA)

# ---- 3. Convert ordered answers to numbers ----
agree = {"strongly disagree": 1, "disagree": 2, "neither agree nor disagree": 3, "agree": 4, "strongly agree": 5}
freq = {"never": 1, "rarely": 2, "sometimes": 3, "often": 4, "very often": 5}
serious = {"not at all serious": 1, "slightly serious": 2, "moderately serious": 3, "very serious": 4, "extremely serious": 5}
influence = {"not at all influential": 1, "slightly influential": 2, "moderately influential": 3,
             "very influential": 4, "extremely influential": 5}
time_ = {"less than 1 hour": 1, "1-2 hours": 2, "2-4 hours": 3, "4-6 hours": 4, "more than 6 hours": 5}

likert = [c for c in df.columns if re.match(r"q\d+_", c)] + ["cyberbullying_important", "culture_blending"]
for c in likert: df[c] = df[c].map(agree)
for c in ["see_gender_conflict_content", "see_social_issue_content", "bullying_frequency", "western_asian_media_freq"]:
    df[c] = df[c].map(freq)
df["bullying_seriousness"] = df["bullying_seriousness"].map(serious)
for c in ["intl_media_success", "intl_media_identity"]: df[c] = df[c].map(influence)
df["social_media_time_score"] = df["social_media_time"].map(time_)

# ---- 4. Scale scores (mean of items) ----
df["gender_conflict_score"] = df[[f"q{n}_gender" for n in range(10, 16)]].mean(axis=1)
df["economic_pressure_score"] = df[[f"q{n}_econ_class" for n in (16, 17, 18)]].mean(axis=1)
df["class_judgment_score"] = df[[f"q{n}_econ_class" for n in range(19, 24)]].mean(axis=1)
df["social_trust_score"] = df[[f"q{n}_trust" for n in range(37, 44)]].mean(axis=1)

# ---- 5. Platforms: one 0/1 column per platform ----
plat = df["platforms"].str.get_dummies(sep=", ").add_prefix("uses_")
df = pd.concat([df, plat], axis=1)
df["n_platforms"] = plat.sum(axis=1)

# ---- 6. Quality flag: nearly identical answers on every Likert item ----
df["straightliner"] = df[likert].nunique(axis=1) <= 2

df.to_csv("survey_clean.csv", index=False)
print(df.shape); print(df[["gender_conflict_score","economic_pressure_score","class_judgment_score","social_trust_score"]].describe().round(2))
print("straightliners:", df.index[df.straightliner].tolist())
