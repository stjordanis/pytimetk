import pandas as pd
import pandas_flavor as pf
from typing import Union, Optional
from functools import partial
import plotly.graph_objects as go

from plotnine import *

from pytimetk.plot.plot_timeseries import plot_timeseries
from pytimetk.utils.plot_helpers import hex_to_rgba, rgba_to_hex, parse_rgba
from pytimetk.utils.checks import check_dataframe_or_groupby, check_date_column, check_anomalize_data
from pytimetk.plot.theme import theme_timetk


    
@pf.register_dataframe_method
def plot_anomalies(
    data: Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy],
    date_column: str,

    facet_ncol: int = 1,
    facet_nrow: Optional[int] = None,
    facet_scales: str = "free_y",
    facet_dir: str = "h", 

    line_color: str = "#2c3e50",
    line_size: Optional[float] = None,
    line_type: str = 'solid',
    line_alpha: float = 1.0,
    
    anom_color: str = "#E31A1C",
    anom_alpha: float = 1.0,
    anom_size: Optional[float] = None,
    
    ribbon_fill: str = "#646464",
    ribbon_alpha: float = 0.2,
    
    y_intercept: Optional[float] = None,
    y_intercept_color: str = "#2c3e50",
    x_intercept: Optional[str] = None,
    x_intercept_color: str = "#2c3e50",
    
    legend_show: bool = True,
    
    title: str = "Anomaly Plot",
    x_lab: str = "",
    y_lab: str = "",
    color_lab: str = "Legend",
    
    x_axis_date_labels: str = "%b %Y",
    base_size: float = 11,
    width: Optional[int] = None,
    height: Optional[int] = None,

    engine: str = 'plotly'
):
    '''The `plot_anomalies` function is used to plot anomalies in a time series data using either Plotly,
    Matplotlib, or Plotnine. See `anomalize()` for the function to prepare the data for plotting.
    
    Parameters
    ----------
    data : Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy]
        The input data for the plot. It can be either a pandas DataFrame or a pandas DataFrameGroupBy object.
    date_column : str
        The `date_column` parameter is a string that specifies the name of the column in the dataframe that contains the dates for the plot.
    facet_ncol : int, optional
        The `facet_ncol` parameter determines the number of columns in the facet grid. It specifies how many subplots will be arranged horizontally in the plot.
    facet_nrow : int
        The `facet_nrow` parameter determines the number of rows in the facet grid. It specifies how many subplots will be arranged vertically in the grid.
    facet_scales : str, optional
        The `facet_scales` parameter determines the scaling of the y-axis in the facetted plots. It can take the following values:
        - "free_y": The y-axis scale will be free for each facet, but the x-axis scale will be fixed for all facets. This is the default value.
        - "free_x": The y-axis scale will be free for each facet, but the x-axis scale will be fixed for all facets.
        - "free": The y-axis scale will be free for each facet (subplot). This is the default value.
        
    facet_dir : str, optional
        The `facet_dir` parameter determines the direction in which the facets (subplots) are arranged. It can take two possible values:
        - "h": The facets will be arranged horizontally (in rows). This is the default value.
        - "v": The facets will be arranged vertically (in columns).
    line_color : str, optional
        The `line_color` parameter is used to specify the color of the lines in the time series plot. It accepts a string value representing a color code or name. The default value is "#2c3e50", which corresponds to a dark blue color.
    line_size : float
        The `line_size` parameter is used to specify the size of the lines in the time series plot. It determines the thickness of the lines.
    line_type : str, optional
        The `line_type` parameter is used to specify the type of line to be used in the time series plot.         
    line_alpha : float
        The `line_alpha` parameter controls the transparency of the lines in the time series plot. It accepts a value between 0 and 1, where 0 means completely transparent (invisible) and 1 means completely opaque (solid).
    anom_color : str, optional
        The `anom_color` parameter is used to specify the color of the anomalies in the plot. It accepts a string value representing a color code or name. The default value is `#E31A1C`, which corresponds to a shade of red.
    anom_alpha : float
        The `anom_alpha` parameter controls the transparency (alpha) of the anomaly points in the plot. It accepts a float value between 0 and 1, where 0 means completely transparent and 1 means completely opaque.
    anom_size : Optional[float]
        The `anom_size` parameter is used to specify the size of the markers used to represent anomalies in the plot. It is an optional parameter, and if not provided, a default value will be used.
    ribbon_fill : str, optional
        The `ribbon_fill` parameter is used to specify the fill color of the ribbon that represents the range of anomalies in the plot. It accepts a string value representing a color code or name.
    ribbon_alpha : float
        The parameter `ribbon_alpha` controls the transparency of the ribbon fill in the plot. It accepts a float value between 0 and 1, where 0 means completely transparent and 1 means completely opaque. A higher value will make the ribbon fill more visible, while a lower value will make it
    y_intercept : float
        The `y_intercept` parameter is used to add a horizontal line to the plot at a specific y-value. It can be set to a numeric value to specify the y-value of the intercept. If set to `None` (default), no y-intercept line will be added to the plot
    y_intercept_color : str, optional
        The `y_intercept_color` parameter is used to specify the color of the y-intercept line in the plot. It accepts a string value representing a color code or name. The default value is "#2c3e50", which corresponds to a dark blue color. You can change this value.
    x_intercept : str
        The `x_intercept` parameter is used to add a vertical line at a specific x-axis value on the plot. It is used to highlight a specific point or event in the time series data. 
        - By default, it is set to `None`, which means no vertical line will be added. 
        - You can use a date string to specify the x-axis value of the intercept. For example, "2020-01-01" would add a vertical line at the beginning of the year 2020.
    x_intercept_color : str, optional
        The `x_intercept_color` parameter is used to specify the color of the vertical line that represents the x-intercept in the plot. By default, it is set to "#2c3e50", which is a dark blue color. You can change this value to any valid color code.
    legend_show : bool, optional
        The `legend_show` parameter is a boolean indicating whether or not to show the legend in the plot. If set to True, the legend will be displayed. The default value is True.
    title : str, optional
        The title of the plot.
    x_lab : str
        The `x_lab` parameter is used to specify the label for the x-axis in the plot. It is a string that represents the label text.
    y_lab : str
        The `y_lab` parameter is used to specify the label for the y-axis in the plot. It is a string that represents the label for the y-axis.
    color_lab : str, optional
        The `color_lab` parameter is used to specify the label for the legend or color scale in the plot. It is used to provide a description of the colors used in the plot, typically when a color column is specified.
    x_axis_date_labels : str, optional
        The `x_axis_date_labels` parameter is used to specify the format of the date labels on the x-axis of the plot. It accepts a string representing the format of the date labels. For  example, "%b %Y" would display the month abbreviation and year (e.g., Jan 2020).
    base_size : float, optional
        The `base_size` parameter is used to set the base font size for the plot. It determines the size of the text elements such as axis labels, titles, and legends.
    width : int
        The `width` parameter is used to specify the width of the plot. It determines the horizontal size of the plot in pixels.
    height : int
        The `height` parameter is used to specify the height of the plot in pixels. It determines the vertical size of the plot when it is rendered.
    engine : str, optional
        The `engine` parameter specifies the plotting library to use for creating the time series plot. It can take one of the following values:
        
        - "plotly" (interactive): Use the plotly library to create the plot. This is the default value.
        - "plotnine" (static): Use the plotnine library to create the plot. This is the default value.
        - "matplotlib" (static): Use the matplotlib library to create the plot.
    
    Returns
    -------
        A plot object, depending on the specified `engine` parameter:
        - If `engine` is set to 'plotnine' or 'matplotlib', the function returns a plot object that can be further customized or displayed. 
        - If `engine` is set to 'plotly', the function returns a plotly figure object.
    
    See Also
    --------
    `anomalize()`: The `anomalize()` function is used to prepare the data for plotting anomalies in a time series data.
    
    Examples
    --------
    ```{python}
    # EXAMPLE 1: SINGLE TIME SERIES
    import pytimetk as tk
    import pandas as pd
    import numpy as np

    # Create a date range
    date_rng = pd.date_range(start='2021-01-01', end='2024-01-01', freq='MS')

    # Generate some random data with a few outliers
    np.random.seed(42)
    data = np.random.randn(len(date_rng)) * 10 + 25  
    data[3] = 100  # outlier

    # Create a DataFrame
    df = pd.DataFrame(date_rng, columns=['date'])
    df['value'] = data
    
    # Anomalize the data
    anomalize_df = tk.anomalize(
        df, "date", "value",
        method = "twitter", 
        iqr_alpha = 0.10, 
        clean_alpha = 0.75,
        clean = "min_max",
    )
    ```
    
    ``` {python}
    # Visualize the anomaly bands, plotly engine
    (
         anomalize_df
            .plot_anomalies(
                date_column = "date",
                engine = "plotly",
            )
    )
    ```
    
    ``` {python}
    # Visualize the anomaly bands, plotly engine
    (
         anomalize_df
            .plot_anomalies(
                date_column = "date",
                engine = "plotnine",
            )
    )
    ```
    
    ``` {python}
    # EXAMPLE 2: MULTIPLE TIME SERIES
    import pytimetk as tk
    import pandas as pd
    
    df = tk.load_dataset("walmart_sales_weekly", parse_dates=["Date"])[["id", "Date", "Weekly_Sales"]]
    
    anomalize_df = (
        df
            .groupby('id') 
            .anomalize(
                "Date", "Weekly_Sales", 
                period = 52, 
                trend = 52, 
                threads = 1
            ) 
    )
    ```
    
    ``` {python}
    # Visualize the anomaly bands, plotly engine
    (
        anomalize_df 
            .groupby(["id"]) 
            .plot_anomalies(
                date_column = "Date", 
                facet_ncol = 2, 
                width = 800,
                height = 800,
                engine = "plotly",
            )
    )
    ```
    
    ``` {python}
    # Visualize the anomaly bands, matplotlib engine
    (
        anomalize_df 
            .groupby(["id"]) 
            .plot_anomalies(
                date_column = "Date", 
                facet_ncol = 2, 
                width = 800,
                height = 800,
                engine = "matplotlib",
            )
    )
    ```
    
    '''
    
    # Check data
    check_dataframe_or_groupby(data)
    check_date_column(data, date_column)
    
    # Check data was anomalized first
    check_anomalize_data(data)
    
    # Handle line_size
    if line_size is None:
        if engine == 'plotnine':
            line_size = 0.35
        elif engine == 'matplotlib':
            line_size = 0.35
        elif engine == 'plotly':
            line_size = 0.65
    
    if engine == 'plotly':
        
        if anom_size is None:
            anom_size = 6.0
        
        
        fig = _plot_anomalies_plotly(
            data = data,
            date_column = date_column,

            facet_ncol = facet_ncol,
            facet_nrow = facet_nrow,
            facet_scales = facet_scales,
            facet_dir = facet_dir, 

            line_color = line_color,
            line_size = line_size,
            line_type = line_type,
            line_alpha = line_alpha,
            
            anom_color = anom_color,
            anom_alpha = anom_alpha,
            anom_size = anom_size,
            
            ribbon_fill = ribbon_fill,
            ribbon_alpha = ribbon_alpha,
            
            y_intercept = y_intercept,
            y_intercept_color = y_intercept_color,
            x_intercept = x_intercept,
            x_intercept_color = x_intercept_color,
            
            legend_show = legend_show,
            
            title = title,
            x_lab = x_lab,
            y_lab = y_lab,
            color_lab = color_lab,
            
            x_axis_date_labels = x_axis_date_labels,
            base_size = base_size,
            width = width,
            height = height,
        )
        
    else:
        
        if anom_size is None:
            anom_size = 1.0
            
        fig = _plot_anomalies_plotnine(
            data = data,
            date_column = date_column,

            facet_ncol = facet_ncol,
            facet_nrow = facet_nrow,
            facet_scales = facet_scales,
            facet_dir = facet_dir, 

            line_color = line_color,
            line_size = line_size,
            line_type = line_type,
            line_alpha = line_alpha,
            
            anom_color = anom_color,
            anom_alpha = anom_alpha,
            anom_size = anom_size,
            
            ribbon_fill = ribbon_fill,
            ribbon_alpha = ribbon_alpha,
            
            y_intercept = y_intercept,
            y_intercept_color = y_intercept_color,
            x_intercept = x_intercept,
            x_intercept_color = x_intercept_color,
            
            legend_show = legend_show,
            
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
            if width == None:
                width_size = 800 # in pixels for compat with plotly
            else: 
                width_size = width

            if height == None:
                height_size = 600 # in pixels for compat with plotly
            else:
                height_size = height
            fig = fig + theme_timetk(height=height_size, width=width_size) # setting default figure size to prevent matplotlib sizing error
            fig = fig.draw()
     
    return fig
    
# Monkey patch the method to pandas groupby objects
pd.core.groupby.generic.DataFrameGroupBy.plot_anomalies = plot_anomalies


def _plot_anomalies_plotly(
    data: Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy],
    date_column: str,

    facet_ncol: int = 1,
    facet_nrow: Optional[int] = None,
    facet_scales: str = "free_y",
    facet_dir: str = "h", 

    line_color: str = "#2c3e50",
    line_size: float = None,
    line_type: str = 'solid',
    line_alpha: float = 1.0,
    
    anom_color: str = "#E31A1C",
    anom_alpha: float = 1.0,
    anom_size: Optional[float] = None,
    
    ribbon_fill: str = "#646464",
    ribbon_alpha: float = 0.2,
    
    y_intercept: Optional[float] = None,
    y_intercept_color: str = "#2c3e50",
    x_intercept: Optional[str] = None,
    x_intercept_color: str = "#2c3e50",
    
    legend_show: bool = True,
    
    title: str = "Anomaly Plot",
    x_lab: str = "",
    y_lab: str = "",
    color_lab: str = "Legend",
    
    x_axis_date_labels: str = "%b %Y",
    base_size: float = 11,
    width: Optional[int] = None,
    height: Optional[int] = None,
    
):
    
    # Plot Setup
    ribbon_color_rgba = hex_to_rgba(ribbon_fill, ribbon_alpha)
    ribbon_color_rgba_list = parse_rgba(ribbon_color_rgba)
    ribbon_color_hex = rgba_to_hex(*ribbon_color_rgba_list)
    
    preload_plot_timeseries = partial(
        plot_timeseries,
                    
        date_column = date_column,
        value_column = "_val", 
        color_column = "_var",
        
        color_palette = [
            line_color, 
            ribbon_color_hex, 
            ribbon_color_hex
        ],
        
        facet_ncol = facet_ncol,
        facet_nrow = facet_nrow,
        facet_scales = facet_scales,
        facet_dir = facet_dir,
        
        line_size = line_size,
        line_type = line_type,
        line_alpha = line_alpha,
        
        y_intercept = y_intercept,
        y_intercept_color = y_intercept_color,
        x_intercept = x_intercept,
        x_intercept_color = x_intercept_color,
        
        smooth = False,
        
        legend_show = legend_show,
        
        title = title,
        x_lab = x_lab,
        y_lab = y_lab,
        color_lab = color_lab,
        
        x_axis_date_labels = x_axis_date_labels,
        
        base_size = base_size,
        
        width = width,
        height = height,
    )
    
    # 1.0 Create Main Plot
    
    is_grouped = False
    if isinstance(data, pd.core.groupby.generic.DataFrameGroupBy):
        group_names = data.grouper.names
        data = data.obj.copy()
        is_grouped = True
    else:
        data = data.copy()
        data["_grp"] = "Time Series"
        group_names = ["_grp"]
    
    
    data[group_names] = data[group_names].astype(str)

    data_prepared = (
        data[[*group_names, date_column, "observed", "recomposed_l1", "recomposed_l2"]] 
            .melt(
                id_vars = [*group_names, date_column], 
                value_name='_val',
                var_name = '_var',
            ) 
            .groupby(group_names) 
    )
    
    fig = preload_plot_timeseries(data_prepared)
                
        
    # 2.0 Add Ribbon
    
    # Create lists to store the indices of the traces
    indices_l1 = [i for i, trace in enumerate(fig.data) if trace.name == 'recomposed_l1']
    indices_l2 = [i for i, trace in enumerate(fig.data) if trace.name == 'recomposed_l2']

    # Iterate through the pairs of indices and update the fig.data list
    for i_l1, i_l2 in zip(indices_l1, indices_l2):
        # Ensure 'recomposed_l1' comes before 'recomposed_l2' in fig.data
        if i_l1 > i_l2:
            i_l1, i_l2 = i_l2, i_l1  # Swap the indices
            fig.data[i_l1], fig.data[i_l2] = fig.data[i_l2], fig.data[i_l1]  # Swap the traces

        # Update the 'recomposed_l2' trace to fill towards 'recomposed_l1'
        fig.data[i_l2].update(fill='tonexty', fillcolor=ribbon_color_rgba)  # Adjust fill color as needed

    # 3.0 Add Anomaly Dots
    
    # Assuming fig.data contains your trace data and you know the number of subplots
    num_subplots = len(fig.layout.annotations)  # Assuming each subplot has one annotation
    
    def generate_triples(n):
        result = []
        for i in range(1, 3*n+1, 3):
            result.append([i, i+1, i+2])
        return result
    
    tripples = generate_triples(num_subplots)

    for tripple in tripples:
        
        observed_data = None
        recomposed_l2_data = None
        recomposed_l1_data = None
        
        for i in tripple:
            i-=1             
            
            # Extract data for each subplot
            
            if fig.data[i].name == 'observed':
                observed_data = fig.data[i]
            elif fig.data[i].name == 'recomposed_l1':
                recomposed_l1_data = fig.data[i]
                fig.data[i].legendgroup = "bands"
                fig.data[i].showlegend = False
            elif fig.data[i].name == 'recomposed_l2':
                recomposed_l2_data = fig.data[i]
                fig.data[i].legendgroup = "bands"
                fig.data[i].showlegend = False

        # Ensure we have the data
        if observed_data and recomposed_l2_data and recomposed_l1_data:
            # Identify points where condition is met
            x_values = []
            y_values = []
            for x, y, y_l2, y_l1 in zip(observed_data.x, observed_data.y, recomposed_l2_data.y, recomposed_l1_data.y):
                if y > y_l2 or y < y_l1:
                    x_values.append(x)
                    y_values.append(y)
            
            # Add scatter plot with identified points to the correct subplot
            fig.add_trace(
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode='markers',
                    marker=dict(
                        color=anom_color, 
                        size=anom_size,
                        opacity=anom_alpha,
                    ),
                    name='anomalies',
                    legendgroup='anomalies',
                    xaxis=observed_data.xaxis,
                    yaxis=observed_data.yaxis
                )
            )
    
    # Remove duplicate legends in each legend group
    seen_legendgroups = set()
    for trace in fig.data:
        legendgroup = trace.legendgroup
        if legendgroup in seen_legendgroups:
            trace.showlegend = False
        else:
            seen_legendgroups.add(legendgroup)
    
    # Cleanup annotations if ungrouped
    if not is_grouped:
        fig['layout']['annotations'] = []
    
    # Apply Styling
    fig.update_annotations(font_size=base_size*0.8)     
    fig.update_traces(hoverlabel=dict(font_size=base_size*0.8))
            
    return fig


def _plot_anomalies_plotnine(
    data: Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy],
    date_column: str,

    facet_ncol: int = 1,
    facet_nrow: Optional[int] = None,
    facet_scales: str = "free_y",
    facet_dir: str = "h", 

    line_color: str = "#2c3e50",
    line_size: float = None,
    line_type: str = 'solid',
    line_alpha: float = 1.0,
    
    anom_color: str = "#E31A1C",
    anom_alpha: float = 1.0,
    anom_size: Optional[float] = None,
    
    ribbon_fill: str = "#646464",
    ribbon_alpha: float = 0.2,
    
    y_intercept: Optional[float] = None,
    y_intercept_color: str = "#2c3e50",
    x_intercept: Optional[str] = None,
    x_intercept_color: str = "#2c3e50",
    
    legend_show: bool = True,
    
    title: str = "Anomaly Plot",
    x_lab: str = "",
    y_lab: str = "",
    color_lab: str = "Legend",
    
    x_axis_date_labels: str = "%b %Y",
    base_size: float = 11,
    width: Optional[int] = None,
    height: Optional[int] = None,
    
):
    
    if isinstance(data, pd.core.groupby.generic.DataFrameGroupBy):
        
        group_names = data.grouper.names
        
        data = data.obj.copy()
        
        if not isinstance(group_names, list):
            group_names = [group_names]
        
        data[group_names] = data[group_names].astype(str) 
        
        data["_group_names"] =  data[group_names].agg(" | ".join, axis=1)
        
    else:
        group_names = None
        data = data.copy()
    
    # 1.0 Canvas
    if group_names is not None:
        g = ggplot(
                data = data,
                mapping = aes(
                    x = date_column,
                    y = "observed",
                    group = "_group_names",
                )
            )
    
    else:
        g = ggplot(
            data = data,
            mapping = aes(
                x = date_column,
                y = "observed",
            )
        )
        
    # 2.0 Add facets
    if group_names is not None:
       g = g + facet_wrap(
            "_group_names",
            ncol = facet_ncol,
            nrow = facet_nrow, 
            scales = facet_scales, 
            dir = facet_dir, 
            shrink = True
        )
    
    # 3.0 Add Ribbons
    g = g + geom_ribbon(
        mapping = aes(
            ymin = "recomposed_l1",
            ymax = "recomposed_l2",
        ),
        alpha = ribbon_alpha,
        fill  = ribbon_fill,
    )
    
    # 4.0 Add Lines
    g = g + \
        geom_line(
            color    = line_color,
            size     = line_size,
            linetype = line_type,
            alpha    = line_alpha
        )
    
    # 5.0 Add Anomalies
    if anom_size is None:
        anom_size = 2.0
    
    g = g + \
        geom_point(
            mapping = aes(
                x = date_column,
                y = "observed",
            ),
            color = anom_color,
            size = anom_size,
            alpha = anom_alpha,
            data = data.query("observed > recomposed_l2 | observed < recomposed_l1"),
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
    
    # Add theme
    g = g + \
        theme_timetk(base_size=base_size, width = width, height = height)
        
    if not legend_show:
        g = g + theme(legend_position='none')
    
    return g
    
    