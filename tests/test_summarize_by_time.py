import numpy as np
import pandas as pd
import pytest
import timetk

@pytest.fixture
def sumarize_by_time_data_test():
    """ A dataframe to test summarize_by_time function"""
    
    data = pd.DataFrame({
        'date': pd.date_range(start='1/1/2020', periods=60),
        'value': np.arange(1, 61, dtype=np.int64),
        'groups': ['Group_1', 'Group_2'] * 30
    })
    
    return data

def test_summarize_by_time_dataframe_functions(sumarize_by_time_data_test):
    """ Test if the aggreagation functions is working"""
    
    data = sumarize_by_time_data_test
    
    # test with one function    
    result = data.summarize_by_time(
        'date', 'value',
        agg_func = 'sum',
        rule = 'M',
        flatten_column_names = False,
        reset_index = False,
    )
    
    expected = pd.DataFrame({
        'date': pd.to_datetime(['2020-01-31', '2020-02-29']),
        'value': [496, 1334]
    }).set_index('date')
    
    assert result.equals(expected), \
        'Aggregate with one function is not working!'

    
    # test with the functions as a list
    result = data.summarize_by_time(
        'date', 'value',
        agg_func = ['sum', 'mean'],
        rule = 'M',
        flatten_column_names = False,
        reset_index = False,
    )
    
    expected = pd.DataFrame({
        'date': pd.to_datetime(['2020-01-31', '2020-02-29']),
        'sum': [496, 1334],
        'mean': [16.0, 46.0]
    }) \
        .set_index('date')
    multilevel_column = [('value', 'sum'), ('value', 'mean')]
    expected.columns = pd.MultiIndex.from_tuples(multilevel_column)    
    
    assert result.equals(expected), \
        'Aggregate with two functions as a list is not working!'
        

def test_summarize_by_time_grouped_functions(sumarize_by_time_data_test):
    """ Test if the aggreagation functions is working"""
    
    data = sumarize_by_time_data_test
    
    # Test groupby objects
    result = data.groupby('groups').summarize_by_time(
        'date', 'value', 
        rule = 'MS', 
        wide_format = True,
        flatten_column_names = False,
        reset_index = False,
    )
    
    cols = pd.MultiIndex(
        levels = [['value'], ['Group_1', 'Group_2']], 
        codes  = list([[0, 0], [0, 1]]),
        names  = [None, 'groups']
    )
    
    idx = pd.DatetimeIndex(['2020-01-01', '2020-02-01'], dtype='datetime64[ns]', name='date', freq='MS')

    expected = pd.DataFrame(
        [[256, 240],[644,690]],
        index = idx,
        columns = cols
    )
    
    assert result.equals(expected), \
        'Aggregate with two functions as a list is not working!'
        