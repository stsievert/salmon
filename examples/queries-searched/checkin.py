import pandas as pd
from pathlib import Path

DATASET = "zappos"
NOISE = "CKL"
dfs = [pd.read_parquet(f) for f in Path("data3/").glob("*.parquet")]
dfs = [df for df in dfs if df.loc[0, "dataset"] == DATASET and df.loc[0, "noise_model"] == NOISE]
df = pd.concat(dfs)
col = "process_answers_calls"
col = "num_ans"
summary = df.pivot_table(index="n_search", values=col)#, values="acc")

#  df.pivot_table(index="num_ans", values="process_answers_calls")
#  df.pivot_table(index="num_ans", values="process_answers_calls")
print(summary)
