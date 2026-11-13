| Config | Model | Accuracy | Easy | Med | Hard | Avg cost | Avg latency | Avg attempts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bare | gemini-3.5-flash-lite | 1/10 | 1/3 | 0/3 | 0/4 | 1.15e-04 | 0.922 | 1.000 |
| schema | gemini-3.5-flash-lite | 9/10 | 3/3 | 3/3 | 3/4 | 5.05e-04 | 0.901 | 1.000 |
| retry | gemini-3.5-flash-lite | 9/10 | 3/3 | 3/3 | 3/4 | 5.08e-04 | 0.830 | 1.000 |

Failed case ids:
- bare / gemini-3.5-flash-lite: employee_count_2003, brazil_customer_count, rock_track_count, acdc_album_count, canada_invoice_total, top_customer, top_genre_revenue, artists_without_albums, invoice_total_by_genre
- schema / gemini-3.5-flash-lite: invoice_total_by_genre
- retry / gemini-3.5-flash-lite: invoice_total_by_genre
