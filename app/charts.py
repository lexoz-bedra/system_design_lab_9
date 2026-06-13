import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

DAY_NAMES = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']


def _fig_to_json(fig) -> dict:
    return json.loads(fig.to_json())



def chart_hourly_trips(df: pd.DataFrame) -> dict:
    hourly = df.groupby('hour').agg(
        trips=('fare_amount', 'count'),
        avg_fare=('fare_amount', 'mean'),
    ).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=hourly['hour'], y=hourly['trips'],
        name='Кол-во поездок', marker_color='#60a5fa', yaxis='y1',
    ))
    fig.add_trace(go.Scatter(
        x=hourly['hour'], y=hourly['avg_fare'].round(2),
        name='Средняя стоимость ($)', mode='lines+markers',
        marker_color='#f59e0b', yaxis='y2',
    ))
    fig.update_layout(
        xaxis_title='Час',
        yaxis=dict(title='Кол-во поездок'),
        yaxis2=dict(title='Средняя стоимость ($)', overlaying='y', side='right'),
        legend=dict(x=0.01, y=0.99),
        template='plotly_dark',
    )
    return _fig_to_json(fig)


def chart_fare_distribution(df: pd.DataFrame) -> dict:
    fig = px.histogram(
        df, x='fare_amount', nbins=60,
        labels={'fare_amount': 'Стоимость ($)'},
        color_discrete_sequence=['#60a5fa'],
        template='plotly_dark',
    )
    fig.update_layout(yaxis_title='Кол-во поездок', showlegend=False)
    return _fig_to_json(fig)


def chart_top_zones(df: pd.DataFrame) -> dict:
    zone_col = 'pickup_zone' if 'pickup_zone' in df.columns else 'pickup_zone_id'
    top = (
        df.groupby(zone_col).size()
        .reset_index(name='trips')
        .sort_values('trips', ascending=False).head(20)
    )
    fig = px.bar(
        top, x='trips', y=zone_col, orientation='h',
        labels={'trips': 'Кол-во поездок', zone_col: 'Зона'},
        color='trips', color_continuous_scale='Blues',
        template='plotly_dark',
    )
    fig.update_layout(
        yaxis={'categoryorder': 'total ascending', 'automargin': True},
        margin={'l': 10, 'r': 20, 't': 10, 'b': 30},
        showlegend=False,
    )
    return _fig_to_json(fig)


def chart_feature_importance(importance: dict) -> dict:
    items = sorted(importance.items(), key=lambda x: x[1])
    fig = go.Figure(go.Bar(
        x=[i[1] for i in items], y=[i[0] for i in items],
        orientation='h', marker_color='#60a5fa',
    ))
    fig.update_layout(xaxis_title='Importance', template='plotly_dark')
    return _fig_to_json(fig)


def chart_heatmap(df: pd.DataFrame) -> dict:
    pivot = (
        df.groupby(['day_of_week', 'hour'])
        .size().reset_index(name='trips')
        .pivot(index='day_of_week', columns='hour', values='trips')
        .fillna(0)
    )
    # ensure all hours 0-23 are present
    for h in range(24):
        if h not in pivot.columns:
            pivot[h] = 0
    pivot = pivot.sort_index()[sorted(pivot.columns)]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[str(h) for h in pivot.columns],
        y=[DAY_NAMES[int(d)] for d in pivot.index],
        colorscale='Blues',
        hovertemplate='Час %{x}, %{y}: %{z:,.0f} поездок<extra></extra>',
    ))
    fig.update_layout(
        xaxis_title='Час суток',
        yaxis_title='',
        template='plotly_dark',
    )
    return _fig_to_json(fig)


def chart_revenue_zones(df: pd.DataFrame) -> dict:
    zone_col = 'pickup_zone' if 'pickup_zone' in df.columns else 'pickup_zone_id'
    top = (
        df.groupby(zone_col)['fare_amount'].sum()
        .reset_index(name='revenue')
        .sort_values('revenue', ascending=False).head(15)
    )
    top['revenue_k'] = (top['revenue'] / 1000).round(1)

    fig = px.bar(
        top, x='revenue_k', y=zone_col, orientation='h',
        labels={'revenue_k': 'Выручка ($K)', zone_col: 'Зона'},
        color='revenue_k', color_continuous_scale='Teal',
        template='plotly_dark',
    )
    fig.update_layout(
        yaxis={'categoryorder': 'total ascending', 'automargin': True},
        margin={'l': 10, 'r': 20, 't': 10, 'b': 30},
        showlegend=False,
    )
    return _fig_to_json(fig)
