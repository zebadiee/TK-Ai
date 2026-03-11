flowchart TD
    subgraph market_alert_graph[market_alert_graph]
        monitor["monitor<br/>clawx_monitor"]
        summary["summary<br/>model_infer"]
        notify["notify<br/>notify"]
    end
    monitor --> summary
    summary --> notify