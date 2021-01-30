import pandas as pd
from pathlib import Path
import gspread
import numpy as np


def read_data(file_name, check_month=str()):
    # sets up package gspread to read sheets from gdrive
    # reads to pandas df
    # checks if worksheet contains multiple sheets,
    # if true creates a list of dfs
    gc = gspread.oauth(flow=gspread.auth.console_flow)
    ss = gc.open(file_name)
    if len(ss.worksheets()) == 1:
        worksheet = ss.get_worksheet(0)
        df = pd.DataFrame(worksheet.get_all_values())
        return df
    elif len(ss.worksheets()) > 1:
        sheets = ss.worksheets()
        dfs = []
        for worksheet in sheets:
            if check_month in worksheet.title:
                dfs.append(pd.DataFrame(worksheet.get_all_values()))
        return dfs


def prep_old_data(read_data_df, value_start_index=(3, 2)):
    # reads in old format equity data file from path;
    # extracts column, index, and count info separately;
    # prepares it for cleaning by creating a multi index;
    # and some small formatting changes
    v_r = value_start_index[0]  # row index of top right value
    v_c = value_start_index[1]  # column index of top right value
    county_names = pd.Index(read_data_df.iloc[v_r:, 0], name="county_names")
    county_names = county_names.dropna()
    if county_names.duplicated().any():
        print("Warning: duplicate counties")
    empty_to_Na_df = read_data_df.replace("", np.NaN)
    dropped_empty_cols_df = empty_to_Na_df.dropna(axis=1, how="all")
    dates = dropped_empty_cols_df.iloc[0, v_c:].str.strip().fillna(method="ffill")
    dates = pd.to_datetime(dates)
    cats = (
        dropped_empty_cols_df.iloc[2, v_c:]
        .str.replace("[ /]", "_", regex=True)
        .str.lower()
        .fillna("-")
    )
    totals = dropped_empty_cols_df.iloc[v_r:, v_c:].values
    multi_cols = pd.MultiIndex.from_frame(
        pd.DataFrame({"dates": dates, "categories": cats})
    )
    rv = pd.DataFrame(totals, columns=multi_cols, index=county_names)
    rv = rv.mask(v <= 1, lambda v: v *  df.iloc[df[v].index, 13] #I feel like this doesn't work, but I'm curious if other people know of a better way to do this
    return rv
    
"""def convert_decimals (df):
    #takes prepped dataframe
    #splits into two dataframes, one with decimal values and one without
    #converts decimal values into case totals
    #merges the two dataframes
    no_decimal_df = ~df.query('asian' <= 1)
    decimal_df = df.query('asian' <= 1)"""


def clean_old_data(df):
    # takes prepped dataframe, filters out total columns
    # removes empty rows
    # stacks it to be long, not wide
    # removes empty rows and duplicate counties
    basic_cols = ~df.columns.get_level_values("categories").str.contains("total")
    simpler_df = df.loc[:, basic_cols]
    not_empty = [(~row.isna().all()) for index, row in simpler_df.iterrows()]
    full_df = simpler_df[not_empty]
    stacked_df = full_df.stack(level=["dates", "categories"])
    if stacked_df.duplicated().any():
        merged_df = merge_duplicates(stacked_df)
        return merged_df
    else:
        return stacked_df

    
def merge_duplicates(df, na_values=("0", "-")):
    # takes stacked_df, finds duplicated indices
    # checks if matching indices have same values, keeps one if true
    # if not same, rejects data, prints indices for review
    noDups = df[df.index.drop_duplicates(keep=False)]  # set aside valid entries
    dups = df[df.index.duplicated(keep=False)]  # identify duplicated indexes
    keepers = []
    rejects = []
    for index, duplicates in dups.groupby(level=[0, 1, 2]):
        if (duplicates == duplicates.iloc[0]).all():
            keepers.append(duplicates.drop_duplicates(keep="first"))
        else:
            rejects.append(duplicates)
    rv = pd.concat([noDups, *keepers])
    if len(rejects) != 0:
        rejects = pd.concat(rejects)
        print(
            "Warning, duplicate entries for these values: \n",
            rejects,
            "\n Above entries rejected.",
        )
    elif rv.index.duplicated().any():
        print(rv.index[rv.index.duplicated()])
        raise Exception("Merge failed, duplicates remaining")
    else:
        print("Duplicates merged successfully")
    return rv


def main():
    file_name = "Historical Data Burst (Nov 23, 2020)"
    dfs = read_data(file_name, "")

    main_file = pd.read_csv(
        Path.cwd().parent / "data/pub_equity_thru_202010.csv",
        index_col=[0, 1, 2],
        parse_dates=True,
        squeeze=True,
    )
    for i in range(0, len(dfs)):
        prepped_data = prep_old_data(dfs[i], value_start_index=(3,3))
        cleaned_data = clean_old_data(prepped_data)
        dfs[i] = cleaned_data
    new = main_file.append(dfs)
    new.rename("totals", inplace=True)
    new.to_csv(Path.cwd().parent / "data/pub_equity_thru_202010_update.csv")
    return new, dfs, main_file


# if __name__ == "__main__":
#     result = main()
