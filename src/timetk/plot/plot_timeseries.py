
import pandas as pd
import numpy as np
import pandas_flavor as pf

from plotnine import *

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from mizani.breaks import date_breaks
from mizani.formatters import date_format

from statsmodels.nonparametric.smoothers_lowess import lowess

from timetk.plot.theme import theme_tq, palette_light
from timetk.utils.plot_helpers import hex_to_rgba


    
@pf.register_dataframe_method
def plot_timeseries(
    data: pd.DataFrame or pd.core.groupby.generic.DataFrameGroupBy,
    date_column,
    value_column,
    
    color_column = None,

    facet_ncol = 1,
    facet_nrow = None,
    facet_scales = "free_y",
    facet_dir = "h", 

    line_color = "#2c3e50",
    line_size = 0.65,
    line_type = 'solid',
    line_alpha = 1,
    
    y_intercept = None,
    y_intercept_color = "#2c3e50",
    x_intercept = None,
    x_intercept_color = "#2c3e50",
    
    smooth = True,
    smooth_color = "#3366FF",
    smooth_frac = 0.2,
    smooth_size = 1.0,
    smooth_alpha = 1,
    
    title = "Time Series Plot",
    x_lab = "",
    y_lab = "",
    color_lab = "Legend",
    
    x_axis_date_labels = "%b %Y",
    base_size = 11,
    width = None,
    height = None,

    engine = 'plotnine'

):   
    '''
    
    Examples
    --------
    ```{python}
    import timetk as tk
    
    df = tk.load_dataset('m4_monthly', parse_dates = ['date'])
    
    # Plotly Object: Single Time Series
    fig = (
        df
            .query('id == "M750"')
            .plot_timeseries(
                'date', 'value', 
                facet_ncol = 1,
                x_axis_date_labels = "%Y",
                engine = 'plotly',
            )
    )
    fig
    
    # Plotly Object: Grouped Time Series
    fig = (
        df
            .groupby('id')
            .plot_timeseries(
                'date', 'value', 
                # color_column = 'id',
                facet_ncol = 1,
                facet_scales = "free_y",
                smooth_frac = 0.2,
                smooth_size = 2.0,
                y_intercept = None,
                x_axis_date_labels = "%Y",
                engine = 'plotly',
                width = 600,
                height = 600,
            )
    )
    fig
    
    # Plotly Object: Color Column
    fig = (
        df
            .plot_timeseries(
                'date', 'value', 
                color_column = 'id',
                smooth = False,
                y_intercept = 0,
                x_axis_date_labels = "%Y",
                engine = 'plotly',
            )
    )
    fig
    
    
    # Plotnine Object: Single Time Series
    fig = (
        df
            .query('id == "M1"')
            .plot_timeseries(
                'date', 'value', 
                x_axis_date_labels = "%Y",
                engine = 'plotnine'
            )
    )
    fig
    
    # Plotnine Object: Grouped Time Series
    fig = (
        df
            .groupby('id')
            .plot_timeseries(
                'date', 'value', 
                color_column = 'id',
                facet_ncol = 2,
                facet_scales = "free",
                line_size = 0.35,
                x_axis_date_labels = "%Y",
                engine = 'plotnine'
            )
    )
    fig
    
    # Plotly Object: Color Column
    fig = (
        df
            .plot_timeseries(
                'date', 'value', 
                color_column = 'id',
                smooth = False,
                y_intercept = 0,
                x_axis_date_labels = "%Y",
                engine = 'plotnine',
            )
    )
    fig
    
    # Matplotlib object
    fig = (
        df
            .groupby('id')
            .plot_timeseries(
                'date', 'value', 
                color_column = 'id',
                facet_ncol = 2,
                x_axis_date_labels = "%Y",
                engine = 'matplotlib'
            )
    )
    fig
    
    ```
    
    '''
    
    # Check if data is a Pandas DataFrame
    if not isinstance(data, pd.DataFrame):
        if not isinstance(data, pd.core.groupby.generic.DataFrameGroupBy):
            raise TypeError("`data` is not a Pandas DataFrame.")
        
    # Handle DataFrames
    if isinstance(data, pd.DataFrame):
        
        group_names = None
        data = data.copy()
        
        # Handle smoother
        if smooth:
            if color_column is None:
                data['__smooth'] = lowess(data[value_column], data[date_column], frac=smooth_frac, return_sorted=False)
            else:
                data['__smooth'] = np.nan
                
                for name, group in data.groupby(color_column):
                    
                    sorted_group = group.sort_values(by=date_column)
                    x = np.arange(len(sorted_group))
                    y = sorted_group[value_column].to_numpy()
                    
                    smoothed = lowess(y, x, frac=smooth_frac)
                    
                    data.loc[sorted_group.index, '__smooth'] = smoothed[:, 1]
        
    
    # Handle GroupBy objects
    if isinstance(data, pd.core.groupby.generic.DataFrameGroupBy):

        group_names = data.grouper.names
        data = data.obj.copy()
        
        # Handle smoother
        if smooth:
            
            data['__smooth'] = np.nan
            
            for name, group in data.groupby(group_names):
                
                sorted_group = group.sort_values(by=date_column)
                x = np.arange(len(sorted_group))
                y = sorted_group[value_column].to_numpy()
                
                smoothed = lowess(y, x, frac=smooth_frac)  # Adjust frac as needed
                
                # Updating the original DataFrame with smoothed values
                data.loc[sorted_group.index, '__smooth'] = smoothed[:, 1]
            
               
    # print(data.head())  
    
    # Engine
    if engine in ['plotnine', 'matplotlib']:
        fig = _plot_timeseries_plotnine(
            data = data,
            date_column = date_column,
            value_column = value_column,
            color_column = color_column,
            group_names = group_names,

            facet_ncol = facet_ncol,
            facet_nrow = facet_nrow,
            facet_scales = facet_scales,
            facet_dir = facet_dir,

            line_color = line_color,
            line_size = line_size,
            line_type = line_type,
            line_alpha = line_alpha,

            y_intercept = y_intercept,
            y_intercept_color = y_intercept_color,
            x_intercept = x_intercept,
            x_intercept_color = x_intercept_color,

            smooth = smooth,
            smooth_color = smooth_color,
            smooth_size = smooth_size,
            smooth_alpha = smooth_alpha,

            title = title,
            x_lab = x_lab,
            y_lab = y_lab,
            color_lab = color_lab,

            x_axis_date_labels = x_axis_date_labels,
            base_size = base_size,
            
            width = width,
            height = height,
        )
        
        if engine == 'matplotlib':
            fig = fig.draw()
        
    elif engine == 'plotly':
        
        fig = _plot_timeseries_plotly(
            data = data,
            date_column = date_column,
            value_column = value_column,
            color_column = color_column,
            group_names = group_names,

            facet_ncol = facet_ncol,
            facet_nrow = facet_nrow,
            facet_scales = facet_scales,
            facet_dir = facet_dir,

            line_color = line_color,
            line_size = line_size,
            line_type = line_type,
            line_alpha = line_alpha,

            y_intercept = y_intercept,
            y_intercept_color = y_intercept_color,
            x_intercept = x_intercept,
            x_intercept_color = x_intercept_color,

            smooth = smooth,
            smooth_color = smooth_color,
            smooth_size = smooth_size,
            smooth_alpha = smooth_alpha,

            title = title,
            x_lab = x_lab,
            y_lab = y_lab,
            color_lab = color_lab,

            x_axis_date_labels = x_axis_date_labels,
            base_size = base_size,
            
            width = width,
            height = height,
        )

    
    return fig

# Monkey patch the method to pandas groupby objects
pd.core.groupby.generic.DataFrameGroupBy.plot_timeseries = plot_timeseries


import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def _plot_timeseries_plotly(
    data,
    date_column,
    value_column,
    
    color_column = None,
    group_names = None,

    facet_ncol = 1,
    facet_nrow = None,
    facet_scales = "free_y",
    facet_dir = "h",

    line_color = "#2c3e50",
    line_size = 0.3,
    line_type = 'solid',
    line_alpha = 1,
    
    y_intercept = None,
    y_intercept_color = "#2c3e50",
    x_intercept = None,
    x_intercept_color = "#2c3e50",
    
    smooth = None,
    smooth_color = "#3366FF",
    smooth_size = 0.3,
    smooth_alpha = 1,
    
    title = "Time Series Plot",
    x_lab = "",
    y_lab = "",
    color_lab = "Legend",
    
    x_axis_date_labels = "%b %Y",
    base_size = 11,
    
    width = None,
    height = None,
):
    
    subplot_titles = []
    if group_names is not None:
        grouped = data.groupby(group_names, sort = False, group_keys = False)
        num_groups = len(grouped)
        facet_nrow = -(-num_groups // facet_ncol)  # Ceil division
        subplot_titles = [" | ".join(map(str, name)) if isinstance(name, tuple) else str(name) for name in grouped.groups.keys()]
        
        if color_column is not None:
            colors = list(palette_light().values()) * 10_000
            colors = colors[:num_groups]
        else: 
            colors = [line_color] * num_groups
        
        
        # print(colors)
        # print(subplot_titles)
        
    else:
        facet_nrow = 1
        num_groups = 1
    
    fig = make_subplots(
        rows=facet_nrow, 
        cols=facet_ncol, 
        subplot_titles=subplot_titles,
        
        # Shared Axes if facet_scales is "free" or "free_x" or "free_y"
        shared_xaxes=True if facet_scales == "free_y" else False,
        shared_yaxes=True if facet_scales == "free_x" else False,
    )

    if group_names is not None:
        for i, (name, group) in enumerate(grouped):
            
            row = i // facet_ncol + 1
            col = i % facet_ncol + 1
            
            # BUG in plotly with "v" direction
            
            # if facet_dir == "h":
            #     row = i // facet_ncol + 1
            #     col = i % facet_ncol + 1
            # else:
            #     col = i // facet_ncol + 1
            #     row = i % facet_ncol + 1

            # BUG - Need to fix color mapping when color_column is not same as group_names
            if color_column is not None:
                trace = go.Scatter(
                    x=group[date_column], 
                    y=group[value_column], 
                    mode='lines',
                    line=dict(color=hex_to_rgba(colors[i], alpha=line_alpha), width=line_size), name=name[0]
                )
                fig.add_trace(trace, row=row, col=col)
                
            else:
                trace = go.Scatter(x=group[date_column], y=group[value_column], mode='lines', line=dict(color=hex_to_rgba(line_color, alpha=line_alpha), width=line_size), showlegend=False, name=name[0])
                fig.add_trace(trace, row=row, col=col)
            
            
            if smooth:
                trace = go.Scatter(x=group[date_column], y=group['__smooth'], mode='lines', line=dict(color=hex_to_rgba(smooth_color, alpha=smooth_alpha), width=smooth_size), showlegend=False, name="Smoother")
                fig.add_trace(trace, row=row, col=col)
            
            if y_intercept is not None:
                fig.add_shape(go.layout.Shape(type="line", y0=y_intercept, y1=y_intercept, x0=group[date_column].min(), x1=group[date_column].max(), line=dict(color=y_intercept_color)), row=row, col=col)
            if x_intercept is not None:
                fig.add_shape(go.layout.Shape(type="line", x0=x_intercept, x1=x_intercept, y0=group[value_column].min(), y1=group[value_column].max(), line=dict(color=x_intercept_color)), row=row, col=col)
                
            # fig.layout.annotations[i].update(text=name[0])
    else:
        
        if color_column is not None:
            
            grouped = data.groupby(color_column, sort = False, group_keys = False)
            num_groups = len(grouped)
            
            colors = list(palette_light().values()) * 10_000
            colors = colors[:num_groups]
            
            for i, (name, group) in enumerate(grouped):
                
                trace = go.Scatter(
                    x=group[date_column], 
                    y=group[value_column], 
                    mode='lines',
                    line=dict(color=hex_to_rgba(colors[i], alpha=line_alpha), width=line_size), name=name[0]
                )
                fig.add_trace(trace)
                
                if smooth:
                    trace = go.Scatter(x=group[date_column], y=group['__smooth'], mode='lines', line=dict(color=hex_to_rgba(smooth_color, alpha=smooth_alpha), width=smooth_size), showlegend=False, name="Smoother")
                    fig.add_trace(trace)
                
                if y_intercept is not None:
                    fig.add_shape(go.layout.Shape(type="line", y0=y_intercept, y1=y_intercept, x0=group[date_column].min(), x1=group[date_column].max(), line=dict(color=y_intercept_color)))
                if x_intercept is not None:
                    fig.add_shape(go.layout.Shape(type="line", x0=x_intercept, x1=x_intercept, y0=group[value_column].min(), y1=group[value_column].max(), line=dict(color=x_intercept_color)))
            
            
        else:
            trace = go.Scatter(x=data[date_column], y=data[value_column], mode='lines', line=dict(color=hex_to_rgba(line_color, alpha=line_alpha), width=line_size), showlegend=False, name="Time Series")
            fig.add_trace(trace)
        
            if smooth:
                trace = go.Scatter(x=data[date_column], y=data['__smooth'], mode='lines', line=dict(color=hex_to_rgba(smooth_color, alpha=smooth_alpha), width=smooth_size), showlegend=False, name="Smoother")
                fig.add_trace(trace)
            
            if y_intercept is not None:
                fig.add_shape(go.layout.Shape(type="line", y0=y_intercept, y1=y_intercept, x0=data[date_column].min(), x1=data[date_column].max(), line=dict(color=y_intercept_color)))
            if x_intercept is not None:
                fig.add_shape(go.layout.Shape(type="line", x0=x_intercept, x1=x_intercept, y0=data[value_column].min(), y1=data[value_column].max(), line=dict(color=x_intercept_color)))

    fig.update_layout(
        title=title,
        xaxis_title=x_lab,
        yaxis_title=y_lab,
        legend_title_text = color_lab,
        xaxis=dict(tickformat=x_axis_date_labels),
    )
    
    fig.update_xaxes(
        matches=None, showticklabels=True, visible=True, 
        # showline=True, linecolor = '#2c3e50', gridcolor = 'lightgrey', mirror=True,
    )
    # fig.update_yaxes(showline=True, linecolor = '#2c3e50', gridcolor = 'lightgrey', mirror=True,)
    
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=40))
    fig.update_layout(
        template="plotly_white", 
        font=dict(size=base_size),
        title_font=dict(size=base_size*1.2),
        legend_title_font=dict(size=base_size*0.8),
        legend_font=dict(size=base_size*0.8),
    )
    fig.update_xaxes(tickfont=dict(size=base_size*0.8))
    fig.update_yaxes(tickfont=dict(size=base_size*0.8))
    fig.update_annotations(font_size=base_size*0.8)
    fig.update_layout(
        autosize=True, 
        width=width,
        height=height,
        # height=200 * num_groups / facet_ncol
    )
    # Update subplot titles (strip) background color to blue
    # for annot in fig.layout.annotations:
    #     annot.update(bgcolor="#2C3E50", font=dict(color='white'))
     
        
    return fig





def _plot_timeseries_plotnine(
    data: pd.DataFrame,
    date_column,
    value_column,
    
    color_column = None,
    group_names = None,

    facet_ncol = 1,
    facet_nrow = None,
    facet_scales = "free_y",
    facet_dir = "h",

    line_color = "#2c3e50",
    line_size = 0.3,
    line_type = 'solid',
    line_alpha = 1,
    
    y_intercept = None,
    y_intercept_color = "#2c3e50",
    x_intercept = None,
    x_intercept_color = "#2c3e50",
    
    smooth = None,
    smooth_color = "#3366FF",
    smooth_size = 0.3,
    smooth_alpha = 1,
    
    title = "Time Series Plot",
    x_lab = "",
    y_lab = "",
    color_lab = "Legend",
    
    x_axis_date_labels = "%b %Y",
    base_size = 11,
    
    
    width = None,
    height = None,
):
    """This is an internal function not meant to be called by the user directly.
    """
    
    # Plot setup
    g = ggplot(
        data = data,
        mapping = aes(
            x = date_column,
            y = value_column
        )
    )

    # Add line
    if color_column is None:
        g = g \
            + geom_line(
                    color    = line_color,
                    size     = line_size,
                    linetype = line_type,
                    alpha    = line_alpha
                )
    else:
        g = g \
            + geom_line(
                    aes(
                        color = color_column
                    ),
                    size     = line_size,
                    linetype = line_type,
                    alpha    = line_alpha
                ) \
            + scale_color_manual(
                values=list(palette_light().values())
            )
    
    # Add a Y-Intercept if desired
    if y_intercept is not None:
        g = g \
            + geom_hline(
                yintercept = y_intercept,
                color = y_intercept_color
        )

    # Add a X-Intercept if desired
    if x_intercept is not None:
        g = g \
            + geom_vline(
                xintercept = x_intercept,
                color = x_intercept_color
        )

    # Add theme & labs
    g = g + labs(x = x_lab, y = y_lab, title = title, color = color_lab)

    # Add scale to X
    g = g + scale_x_datetime(date_labels = x_axis_date_labels)

    # Add facets
    if group_names is not None:
       g = g + facet_wrap(
            group_names,
            ncol = facet_ncol,
            nrow = facet_nrow, 
            scales = facet_scales, 
            dir = facet_dir, 
            shrink = True
        )
       
    # Add smoother
    if smooth:
        if color_column is None:
            g = g + geom_line(
                aes(
                    y = '__smooth'
                ),
                color = smooth_color,
                size = smooth_size,
                alpha = smooth_alpha
            )
        else:
            g = g + geom_line(
                aes(
                    y = '__smooth',
                    group = color_column
                ),
                color = smooth_color,
                size = smooth_size,
                alpha = smooth_alpha
            )

    # Add theme
    g = g + \
        theme_tq(base_size=base_size, width = width, height = height) 
    
    return g
    

    
    
    
    
    
    