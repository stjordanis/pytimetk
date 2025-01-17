import pandas as pd
import polars as pl
import pandas_flavor as pf
import numpy as np
import inspect
import warnings

from typing import Union, Optional, Callable, Tuple, List

from pathos.multiprocessing import ProcessingPool
from functools import partial

from pytimetk.utils.checks import check_dataframe_or_groupby, check_date_column, check_value_column
from pytimetk.utils.parallel_helpers import conditional_tqdm, get_threads
from pytimetk.utils.polars_helpers import update_dict

@pf.register_dataframe_method
def augment_rolling(
    data: Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy], 
    date_column: str, 
    value_column: Union[str, list],  
    window_func: Union[str, list, Tuple[str, Callable]] = 'mean',
    window: Union[int, tuple, list] = 2,
    min_periods: Optional[int] = None,
    engine: str = 'pandas',
    center: bool = False,
    threads: int = 1,
    show_progress: bool = True,
    **kwargs,
) -> pd.DataFrame:
    '''
    Apply one or more Series-based rolling functions and window sizes to one or more columns of a DataFrame.
    
    Parameters
    ----------
    data : Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy]
        Input data to be processed. Can be a Pandas DataFrame or a GroupBy 
        object.
    date_column : str
        Name of the datetime column. Data is sorted by this column within each 
        group.
    value_column : Union[str, list]
        Column(s) to which the rolling window functions should be applied. Can 
        be a single column name or a list.
    window_func : Union[str, list, Tuple[str, Callable]], optional, default 'mean'
        The `window_func` parameter in the `augment_rolling` function specifies 
        the function(s) to be applied to the rolling windows of the value 
        column(s).

        1. It can be either:
            - A string representing the name of a standard function (e.g., 
              'mean', 'sum').
            
        2. For custom functions:
            - Provide a list of tuples. Each tuple should contain a custom name 
              for the function and the function itself.
            - Each custom function should accept a Pandas Series as its input 
              and operate on that series.
              Example: ("range", lambda x: x.max() - x.min())
        
        (See more Examples below.)

        Note: If your function needs to operate on multiple columns (i.e., it 
              requires access to a DataFrame rather than just a Series), 
              consider using the `augment_rolling_apply` function in this library.   
    window : Union[int, tuple, list], optional, default 2
        Specifies the size of the rolling windows.
        - An integer applies the same window size to all columns in `value_column`.
        - A tuple generates windows from the first to the second value (inclusive).
        - A list of integers designates multiple window sizes for each respective 
          column.
    min_periods : int, optional, default None
        Minimum observations in the window to have a value. Defaults to the 
        window size. If set, a value will be produced even if fewer observations 
        are present than the window size.
    engine : str, optional, default 'pandas'
        Specifies the backend computation library for augmenting expanding window 
        functions. 
    
        The options are:
            - "pandas" (default): Uses the `pandas` library.
            - "polars": Uses the `polars` library, which may offer performance 
               benefits for larger datasets.
    
    center : bool, optional, default False
        If `True`, the rolling window will be centered on the current value. For 
        even-sized windows, the window will be left-biased. Otherwise, it uses a trailing window.
    threads : int, optional, default 1
        Number of threads to use for parallel processing. If `threads` is set to 
        1, parallel processing will be disabled. Set to -1 to use all available CPU cores.
    show_progress : bool, optional, default True
        If `True`, a progress bar will be displayed during parallel processing.
    
    Returns
    -------
    pd.DataFrame
        The `augment_rolling` function returns a DataFrame with new columns for 
        each applied function, window size, and value column.
    
    Notes
    -----
    ## Performance
    
    This function uses parallel processing to speed up computation for large 
    datasets with many time series groups: 
    
    Parallel processing has overhead and may not be faster on small datasets.
    
    To use parallel processing, set `threads = -1` to use all available processors.
    
    Examples
    --------
    ```{python}
    import pytimetk as tk
    import pandas as pd
    import numpy as np
    
    df = tk.load_dataset("m4_daily", parse_dates = ['date'])
    ```
    
    ```{python}
    # Example 1 - Using a single window size and a single function name, pandas engine
    # This example demonstrates the use of both string-named functions and lambda 
    # functions on a rolling window. We specify a list of window sizes: [2,7]. 
    # As a result, the output will have computations for both window sizes 2 and 7.
    # Note - It's preferred to use built-in or configurable functions instead of 
    # lambda functions for performance reasons.

    rolled_df = (
        df
            .groupby('id')
            .augment_rolling(
                date_column = 'date', 
                value_column = 'value', 
                window = [2,7],  # Specifying multiple window sizes
                window_func = [
                    'mean',  # Built-in mean function
                    ('std', lambda x: x.std())  # Lambda function to compute standard deviation
                ],
                threads = 1,  # Disabling parallel processing
                engine = 'pandas'  # Using pandas engine
            )
    )
    display(rolled_df)
    ```
    
    ```{python}
    # Example 2 - Multiple groups, pandas engine
    # Example showcasing the use of string function names and lambda functions 
    # applied on rolling windows. The `window` tuple (1,3) will generate window 
    # sizes of 1, 2, and 3.
    # Note - It's preferred to use built-in or configurable functions instead of 
    # lambda functions for performance reasons.
    
    rolled_df = (
        df
            .groupby('id')
            .augment_rolling(
                date_column = 'date', 
                value_column = 'value', 
                window = (1,3),  # Specifying a range of window sizes
                window_func = [
                    'mean',  # Using built-in mean function
                    ('std', lambda x: x.std())  # Lambda function for standard deviation
                ],
                threads = 1,  # Disabling parallel processing
                engine = 'pandas'  # Using pandas engine
            )
    )
    display(rolled_df) 
    ```
    
    ```{python}
    # Example 3 - Multiple groups, polars engine
    
    rolled_df = (
        df
            .groupby('id')
            .augment_rolling(
                date_column = 'date', 
                value_column = 'value', 
                window = (1,3),  # Specifying a range of window sizes
                window_func = [
                    'mean',  # Using built-in mean function
                    'std',  # Using built-in standard deviation function
                ],
                engine = 'polars'  # Using polars engine
            )
    )
    display(rolled_df) 
    ```
    '''
    # Checks
    check_dataframe_or_groupby(data)
    check_date_column(data, date_column)
    check_value_column(data, value_column)
    
    # Convert string value column to list for consistency
    if isinstance(value_column, str):
        value_column = [value_column]
    
    # Validate window argument and convert it to a consistent list format
    if not isinstance(window, (int, tuple, list)):
        raise TypeError("`window` must be an integer, tuple, or list.")
    if isinstance(window, int):
        window = [window]
    elif isinstance(window, tuple):
        window = list(range(window[0], window[1] + 1))
    
    # Get threads
    threads = get_threads(threads)    
    
    # Convert single window function to list for consistent processing    
    if isinstance(window_func, (str, tuple)):
        window_func = [window_func]
    
    # Call the function to augment rolling window columns using the specified engine
    if engine == 'pandas':
        return _augment_rolling_pandas(
            data, 
            date_column, 
            value_column, 
            window_func, 
            window, 
            min_periods, 
            center, 
            threads, 
            show_progress,
            **kwargs
        )
    elif engine == 'polars':
        return _augment_rolling_polars(
            data, 
            date_column, 
            value_column, 
            window_func,
            window, 
            min_periods,
            center,
            threads,
            show_progress,
            **kwargs
        )
    else:
        raise ValueError("Invalid engine. Use 'pandas' or 'polars'.")
    
# Monkey patch the method to pandas groupby objects
pd.core.groupby.generic.DataFrameGroupBy.augment_rolling = augment_rolling
    
def _augment_rolling_pandas(
    data: Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy], 
    date_column: str, 
    value_column: Union[str, list],  
    window_func: Union[str, list, Tuple[str, Callable]] = 'mean',
    window: Union[int, tuple, list] = 2,
    min_periods: Optional[int] = None,
    center: bool = False,
    threads: int = 1,
    show_progress: bool = True,
    **kwargs,
) -> pd.DataFrame:
    
    # Create a fresh copy of the data, leaving the original untouched
    data_copy = data.copy() if isinstance(data, pd.DataFrame) else data.obj.copy()
    
    # Group data if it's a GroupBy object; otherwise, prepare it for the rolling calculations
    if isinstance(data, pd.core.groupby.generic.DataFrameGroupBy):
        group_names = data.grouper.names
        grouped = data_copy.sort_values(by=[*group_names, date_column]).groupby(group_names)
        
        # Check if the data is grouped and threads are set to 1. If true, handle it without parallel processing.
        if threads == 1:
            func = partial(_process_single_roll, 
                           value_column=value_column, 
                           window_func=window_func, 
                           window=window, 
                           min_periods=min_periods, 
                           center=center, **kwargs)

            # Use tqdm to display progress for the loop
            result_dfs = [func(group) for _, group in conditional_tqdm(grouped, total=len(grouped), desc="Calculating Rolling...", display=show_progress)]
        else:
            # Prepare to use pathos.multiprocessing
            pool = ProcessingPool(threads)

            # Use partial to "freeze" arguments for _process_single_roll
            func = partial(_process_single_roll, 
                           value_column=value_column, 
                           window_func=window_func, 
                           window=window, 
                           min_periods=min_periods, 
                           center=center, **kwargs)

            result_dfs = list(conditional_tqdm(pool.map(func, (group for _, group in grouped)), 
                                               total=len(grouped), 
                                               desc="Calculating Rolling...", 
                                               display=show_progress))
    else:
        result_dfs = [_process_single_roll(data_copy, value_column, window_func, window, min_periods, center, **kwargs)]
    
    result_df = pd.concat(result_dfs).sort_index()  # Sort by the original index
    return result_df


def _augment_rolling_polars(
    data: Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy], 
    date_column: str, 
    value_column: Union[str, list],  
    window_func: Union[str, list, Tuple[str, Callable]] = 'mean',
    window: Union[int, tuple, list] = 2,
    min_periods: Optional[int] = None,
    center: bool = False,
    threads: int = 1,
    show_progress: bool = True,
    **kwargs,
) -> pd.DataFrame:
    
    # Create a fresh copy of the data, leaving the original untouched
    data_copy = data.copy() if isinstance(data, pd.DataFrame) else data.obj.copy()
    
    # Retrieve the group column names if the input data is a GroupBy object
    if isinstance(data, pd.core.groupby.generic.DataFrameGroupBy):
        group_names = data.grouper.names
    else: 
        group_names = None

    # Convert data into a Pandas DataFrame format for processing
    if isinstance(data_copy, pd.core.groupby.generic.DataFrameGroupBy):
        pandas_df = data_copy.apply(lambda x: x)
    elif isinstance(data_copy, pd.DataFrame):
        pandas_df = data_copy
    else:
        raise ValueError("Data must be a Pandas DataFrame or Pandas GroupBy object.")
    
    # Initialize lists to store rolling expressions and new column names  
    rolling_exprs = []
    new_column_names = []

    # Construct rolling expressions for each column and function combination
    for col in value_column:
        for window_size in window:
            min_periods = window_size if min_periods is None else min_periods
            for func in window_func:
                
                # Handle functions passed as tuples
                if isinstance(func, tuple):
                    # Ensure the tuple is of length 2 and begins with a string
                    if len(func) != 2:
                        raise ValueError(f"Expected tuple of length 2, but `window_func` received tuple of length {len(func)}.")
                    if not isinstance(func[0], str):
                        raise TypeError(f"Expected first element of tuple to be type 'str', but `window_func` received {type(func[0])}.")
                    
                    user_func_name, func = func
                    new_column_name = f"{col}_rolling_{user_func_name}_win_{window_size}"
                    
                    # Try handling a lambda function of the form lambda x: x
                    if inspect.isfunction(func) and len(inspect.signature(func).parameters) == 1:
                        try:
                            # Construct rolling window expression
                            rolling_expr = pl.col(col) \
                                .cast(pl.Float64) \
                                .rolling_apply(
                                    function=func,
                                    window_size=window_size, 
                                    min_periods=min_periods
                                )
                        except Exception as e:
                            raise Exception(f"An error occurred during the operation of the `{user_func_name}` function in Polars. Error: {e}")
    
                    # Try handling a configurable function (e.g. pl_quantile) if it is not a lambda function
                    elif isinstance(func, tuple) and func[0] == 'configurable':
                        try:
                            # Configurable function should return 4 objects
                            _, func_name, default_kwargs, user_kwargs = func
                        except Exception as e:
                            raise ValueError(f"Unexpected function format. Expected a tuple with format ('configurable', func_name, default_kwargs, user_kwargs). Received: {func}. Original error: {e}")
                        
                        try:
                            # Define local values that may be required by configurable functions.
                            # If adding a new configurable function in utils.polars_helpers that necessitates 
                            # additional local values, consider updating this dictionary accordingly.
                            local_values = {
                                'window_size': window_size,
                                'min_periods': min_periods
                            }
                            # Combine local values with user-provided parameters for the configurable function
                            user_kwargs.update(local_values)
                            # Update the default configurable parameters (without adding new keys)
                            default_kwargs = update_dict(default_kwargs, user_kwargs)
                        except Exception as e:
                            raise ValueError("Error encountered while updating parameters for the configurable function `{func_name}` passed to `window_func`: {e}")
                        
                        try:
                            # Construct rolling window expression
                            rolling_expr = getattr(pl.col(col), f"rolling_{func_name}")(**default_kwargs)
                        except AttributeError as e:
                            raise AttributeError(f"The function `{user_func_name}` tried to access a non-existent attribute or method in Polars. Error: {e}")
                        except Exception as e:
                            raise Exception(f"Error during the execution of `{user_func_name}` in Polars. Error: {e}")
                    
                    else:
                        raise TypeError(f"Unexpected function format for `{user_func_name}`.")
                    
                    rolling_expr = rolling_expr.alias(new_column_name)

                elif isinstance(func, str):
                    func_name = func
                    new_column_name = f"{col}_rolling_{func_name}_win_{window_size}"
                    if not hasattr(pl.col(col), f"{func_name}"):
                        raise ValueError(f"{func_name} is not a recognized function for Polars.")
                    
                    # Construct rolling window expression and handle specific case of 'skew'
                    if func_name == "skew":
                        rolling_expr = getattr(pl.col(col), f"rolling_{func_name}")(window_size=window_size)
                    elif func_name == "quantile":
                            new_column_name = f"{col}_rolling_{func}_50_win_{window_size}"
                            rolling_expr = getattr(pl.col(col), f"rolling_{func_name}")(quantile=0.5, window_size=window_size, min_periods=min_periods, interpolation='midpoint')
                            warnings.warn(
                                "You passed 'quantile' as a string-based function, so it defaulted to a 50 percent quantile (0.5). "
                                "For more control over the quantile value, consider using the function `pl_quantile()`. "
                                "For example: ('quantile_75', pl_quantile(quantile=0.75))."
                            )
                    else: 
                        rolling_expr = getattr(pl.col(col), f"rolling_{func_name}")(window_size=window_size, min_periods=min_periods)

                    rolling_expr = rolling_expr.alias(new_column_name)
                    
                else:
                    raise TypeError(f"Invalid function type: {type(func)}")
                
                # Add constructed expressions and new column names to respective lists
                rolling_exprs.append(rolling_expr)
                new_column_names.append(new_column_name)

    # Convert Pandas DataFrame to Polars and ensure a consistent row order by resetting the index
    df = pl.from_pandas(pandas_df.reset_index())
    
    # Evaluate the accumulated rolling expressions and convert back to a Pandas DataFrame
    if group_names:
        df_new_columns = df \
            .sort(*group_names, date_column) \
            .group_by(group_names) \
            .agg(rolling_exprs) \
            .sort(*group_names) \
            .explode(new_column_names)

        df = pl.concat([df, df_new_columns.drop(group_names)], how="horizontal") \
                .sort('index') \
                .drop('index') \
                .to_pandas()
    else:
        df = df \
            .sort(date_column) \
            .with_columns(rolling_exprs) \
            .sort('index') \
            .drop('index') \
            .to_pandas()
                
    return df


@pf.register_dataframe_method
def augment_rolling_apply(
    data: Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy], 
    date_column: str,
    window_func: Union[Tuple[str, Callable], List[Tuple[str, Callable]]], 
    window: Union[int, tuple, list] = 2, 
    min_periods: Optional[int] = None,
    center: bool = False,
    threads: int = 1,
    show_progress: bool = True,
) -> pd.DataFrame:
    '''
    Apply one or more DataFrame-based rolling functions and window sizes to one 
    or more columns of a DataFrame.
    
    Parameters
    ----------
    data : Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy]
        Input data to be processed. Can be a Pandas DataFrame or a GroupBy object.
    date_column : str
        Name of the datetime column. Data is sorted by this column within each 
        group.
    window_func : Union[Tuple[str, Callable], List[Tuple[str, Callable]]]
        The `window_func` parameter in the `augment_rolling_apply` function 
        specifies the function(s) that operate on a rolling window with the 
        consideration of multiple columns.

        The specification can be:
        - A tuple where the first element is a string representing the function's 
          name and the second element is the callable function itself.
        - A list of such tuples for multiple functions.
        
        (See more Examples below.)

        Note: For functions targeting only a single value column without the 
        need for contextual data from other columns, consider using the 
        `augment_rolling` function in this library.
    window : Union[int, tuple, list], optional
        Specifies the size of the rolling windows.
        - An integer applies the same window size to all columns in `value_column`.
        - A tuple generates windows from the first to the second value (inclusive).
        - A list of integers designates multiple window sizes for each respective 
          column.
    min_periods : int, optional, default None
        Minimum observations in the window to have a value. Defaults to the 
        window size. If set, a value will be produced even if fewer observations 
        are present than the window size.
    center : bool, optional
        If `True`, the rolling window will be centered on the current value. For 
        even-sized windows, the window will be left-biased. Otherwise, it uses a 
        trailing window.
    threads : int, optional, default 1
        Number of threads to use for parallel processing. If `threads` is set to 
        1, parallel processing will be disabled. Set to -1 to use all available 
        CPU cores.
    show_progress : bool, optional, default True
        If `True`, a progress bar will be displayed during parallel processing.
    
    Returns
    -------
    pd.DataFrame
        The `augment_rolling` function returns a DataFrame with new columns for 
        each applied function, window size, and value column.
        
    Notes
    -----
    ## Performance
    
    This function uses parallel processing to speed up computation for large 
    datasets with many time series groups: 
    
    Parallel processing has overhead and may not be faster on small datasets.
    
    To use parallel processing, set `threads = -1` to use all available processors.
    
    
    Examples
    --------
    ```{python}
    import pytimetk as tk
    import pandas as pd
    import numpy as np

    # Example 1 - showcasing the rolling correlation between two columns 
    # (`value1` and `value2`).
    # The correlation requires both columns as input.
    
    # Sample DataFrame with id, date, value1, and value2 columns.
    df = pd.DataFrame({
        'id': [1, 1, 1, 2, 2, 2],
        'date': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05', '2023-01-06']),
        'value1': [10, 20, 29, 42, 53, 59],
        'value2': [2, 16, 20, 40, 41, 50],
    })
    
    # Compute the rolling correlation for each group of 'id'
    # Using a rolling window of size 3 and a lambda function to calculate the 
    # correlation.
    
    rolled_df = (
        df.groupby('id')
        .augment_rolling_apply(
            date_column='date',
            window=3,
            window_func=[('corr', lambda x: x['value1'].corr(x['value2']))],  # Lambda function for correlation
            center = False,  # Not centering the rolling window
            threads = 1 # Increase threads for parallel processing (use -1 for all cores)
        )
    )
    display(rolled_df)
    ```
    
    ```{python}
    # Example 2 - Rolling Regression Example: Using `value1` as the dependent 
    # variable and `value2` and `value3` as the independent variables. This 
    # example demonstrates how to perform a rolling regression using two 
    # independent variables.

    # Sample DataFrame with `id`, `date`, `value1`, `value2`, and `value3` columns.
    df = pd.DataFrame({
        'id': [1, 1, 1, 2, 2, 2],
        'date': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05', '2023-01-06']),
        'value1': [10, 20, 29, 42, 53, 59],
        'value2': [5, 16, 24, 35, 45, 58],
        'value3': [2, 3, 6, 9, 10, 13]
    })
    
    # Define Regression Function to be applied on the rolling window.
    def regression(df):
    
        # Required module (scikit-learn) for regression.
        # This import statement is required inside the function to avoid errors.
        from sklearn.linear_model import LinearRegression
    
        model = LinearRegression()
        X = df[['value2', 'value3']]  # Independent variables
        y = df['value1']  # Dependent variable
        model.fit(X, y)
        ret = pd.Series([model.intercept_, model.coef_[0]], index=['Intercept', 'Slope'])
        
        return ret # Return intercept and slope as a Series
        
    # Compute the rolling regression for each group of `id`
    # Using a rolling window of size 3 and the regression function.
    rolled_df = (
        df.groupby('id')
        .augment_rolling_apply(
            date_column='date',
            window=3,
            window_func=[('regression', regression)]
        )
        .dropna()
    )

    # Format the results to have each regression output (slope and intercept) in 
    # separate columns.
    
    regression_wide_df = pd.concat(rolled_df['rolling_regression_win_3'].to_list(), axis=1).T
    
    regression_wide_df = pd.concat([rolled_df.reset_index(drop = True), regression_wide_df], axis=1)
    
    display(regression_wide_df)
    ```
    '''
    # Ensure data is a DataFrame or a GroupBy object
    check_dataframe_or_groupby(data)
    
    # Ensure date column exists and is properly formatted
    check_date_column(data, date_column)
    
    # Get threads
    threads = get_threads(threads)
    
    # Validate window argument and convert it to a consistent list format
    if not isinstance(window, (int, tuple, list)):
        raise TypeError("`window` must be an integer, tuple, or list.")
    if isinstance(window, int):
        window = [window]
    elif isinstance(window, tuple):
        window = list(range(window[0], window[1] + 1))
    
    # Convert single window function to list for consistent processing    
    if isinstance(window_func, (str, tuple)):
        window_func = [window_func]
    
     # Create a fresh copy of the data, leaving the original untouched
    data_copy = data.copy() if isinstance(data, pd.DataFrame) else data.obj.copy()
    
    original_index = data_copy.index
    
    # Group data if it's a GroupBy object; otherwise, prepare it for the rolling calculations
    if isinstance(data, pd.core.groupby.generic.DataFrameGroupBy):
        group_names = data.grouper.names
        grouped = data_copy.sort_values(by=[*group_names, date_column]).groupby(group_names)
    else: 
        group_names = None
        grouped = [([], data_copy.sort_values(by=[date_column]))]

    if threads == 1:
        result_dfs = []
        for group in conditional_tqdm(grouped, total=len(grouped), desc="Processing rolling apply...", display= show_progress):
            args = group, window, window_func, min_periods, center
            result_dfs.append(_process_single_apply_group(args))
    else:
        # Prepare to use pathos.multiprocessing
        pool = ProcessingPool(threads)
        args = [(group, window, window_func, min_periods, center) for group in grouped]
        result_dfs = list(conditional_tqdm(pool.map(_process_single_apply_group, args), 
                                        total=len(grouped), 
                                        desc="Processing rolling apply...", 
                                        display=show_progress))

    # Combine processed dataframes and sort by index
    result_df = pd.concat(result_dfs).sort_index()

    # result_df = pd.concat([data_copy, result_df], axis=1)
    result_df = pd.concat([data_copy.reset_index(drop=True), result_df.reset_index(drop=True)], axis=1)
    result_df.index = original_index

    return result_df

# Monkey patch the method to pandas groupby objects
pd.core.groupby.generic.DataFrameGroupBy.augment_rolling_apply = augment_rolling_apply



# UTILITIES
# ---------
def _process_single_apply_group(args):
    
    group, window, window_func, min_periods, center = args
    
    name, group_df = group
    results = {}
    for window_size in window:
        min_periods = window_size if min_periods is None else min_periods
        for func in window_func:
            if isinstance(func, tuple):
                func_name, func = func
                new_column_name = f"rolling_{func_name}_win_{window_size}"
                results[new_column_name] = _rolling_apply(func, group_df, window_size, min_periods=min_periods, center=center)["result"]
            else:
                raise TypeError(f"Expected 'tuple', but got invalid function type: {type(func)}")
    return pd.DataFrame(results, index=group_df.index)

def _rolling_apply(func, df, window_size, center, min_periods):
        
    num_rows = len(df)
    results = [np.nan] * num_rows
    adjusted_window = window_size // 2 if center else window_size - 1  # determine the offset for centering
    
    for center_point in range(num_rows):
        if center:
            if window_size % 2 == 0:  # left biased window if window size is even
                start = max(0, center_point - adjusted_window)
                end = min(num_rows, center_point + adjusted_window)
            else: 
                start = max(0, center_point - adjusted_window)
                end = min(num_rows, center_point + adjusted_window + 1)
        else:
            start = max(0, center_point - adjusted_window)
            end = center_point + 1
        
        window_df = df.iloc[start:end]
        
        if min_periods is None:
            min_periods = window_size
        
        if len(window_df) >= min_periods:
            results[center_point if center else end - 1] = func(window_df)
    
    return pd.DataFrame({'result': results}, index=df.index)

def _process_single_roll(group_df, value_column, window_func, window, min_periods, center, **kwargs):
    result_dfs = []
    for value_col in value_column:
        for window_size in window:
            min_periods = window_size if min_periods is None else min_periods
            for func in window_func:
                if isinstance(func, tuple):
                    # Ensure the tuple is of length 2 and begins with a string
                    if len(func) != 2:
                        raise ValueError(f"Expected tuple of length 2, but `window_func` received tuple of length {len(func)}.")
                    if not isinstance(func[0], str):
                        raise TypeError(f"Expected first element of tuple to be type 'str', but `window_func` received {type(func[0])}.")
                
                    user_func_name, func = func
                    new_column_name = f"{value_col}_rolling_{user_func_name}_win_{window_size}"
                        
                    # Try handling a lambda function of the form lambda x: x
                    if inspect.isfunction(func) and len(inspect.signature(func).parameters) == 1:
                        try:
                            # Construct rolling window column
                            group_df[new_column_name] = group_df[value_col].rolling(window=window_size, min_periods=min_periods, center=center, **kwargs).apply(func, raw=True)
                        except Exception as e:
                            raise Exception(f"An error occurred during the operation of the `{user_func_name}` function in Pandas. Error: {e}")

                    # Try handling a configurable function (e.g. pd_quantile)
                    elif isinstance(func, tuple) and func[0] == 'configurable':
                        try:
                            # Configurable function should return 4 objects
                            _, func_name, default_kwargs, user_kwargs = func
                        except Exception as e:
                            raise ValueError(f"Unexpected function format. Expected a tuple with format ('configurable', func_name, default_kwargs, user_kwargs). Received: {func}. Original error: {e}")
                        
                        try:
                            # Define local values that may be required by configurable functions.
                            # If adding a new configurable function in utils.pandas_helpers that necessitates 
                            # additional local values, consider updating this dictionary accordingly.
                            local_values = {}
                            # Combine local values with user-provided parameters for the configurable function
                            user_kwargs.update(local_values)
                            # Update the default configurable parameters (without adding new keys)
                            default_kwargs = update_dict(default_kwargs, user_kwargs)
                        except Exception as e:
                            raise ValueError("Error encountered while updating parameters for the configurable function `{func_name}` passed to `window_func`: {e}")
                        
                        try:
                            # Get the rolling window function 
                            rolling_function = getattr(group_df[value_col].rolling(window=window_size, min_periods=min_periods, center=center, **kwargs), func_name, None)
                        except Exception as e:
                            raise AttributeError(f"The function `{func_name}` tried to access a non-existent attribute or method in Pandas. Error: {e}")

                        if rolling_function:
                            try:
                                # Apply rolling function to data and store in new column
                                group_df[new_column_name] = rolling_function(**default_kwargs)
                            except Exception as e:
                                raise Exception(f"Failed to construct the rolling window column using function `{user_func_name}`. Error: {e}")
                    else:
                        raise TypeError(f"Unexpected function format for `{user_func_name}`.")
            
                elif isinstance(func, str):
                    new_column_name = f"{value_col}_rolling_{func}_win_{window_size}"
                    # Get the rolling function (like mean, sum, etc.) specified by `func` for the given column and window settings
                    if func == "quantile":
                        new_column_name = f"{value_col}_rolling_{func}_50_win_{window_size}"
                        group_df[new_column_name] = group_df[value_col].rolling(window=window_size, min_periods=min_periods, center=center, **kwargs).quantile(q=0.5)
                        warnings.warn(
                            "You passed 'quantile' as a string-based function, so it defaulted to a 50 percent quantile (0.5). "
                            "For more control over the quantile value, consider using the function `pd_quantile()`. "
                            "For example: ('quantile_75', pd_quantile(q=0.75))."
                        )
                    else:
                        rolling_function = getattr(group_df[value_col].rolling(window=window_size, min_periods=min_periods, center=center, **kwargs), func, None)
                        # Apply rolling function to data and store in new column
                        if rolling_function:
                            group_df[new_column_name] = rolling_function()
                        else:
                            raise ValueError(f"Invalid function name: {func}")
                else:
                    raise TypeError(f"Invalid function type: {type(func)}") 
          
        result_dfs.append(group_df)
    return pd.concat(result_dfs)
