using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Windows;
using System.Windows.Data;
using System.Windows.Media;
using AFMI_Gestion_projet.Services;

namespace AFMI_Gestion_projet.Converters
{
    public class SCurveToPointsConverter : IValueConverter
    {
        public string LineType { get; set; } = "PV"; // PV, EV, AC
        public double CanvasWidth { get; set; } = 600;
        public double CanvasHeight { get; set; } = 200;

        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            var points = new PointCollection();
            try
            {
                if (value is not List<SCurvePoint> data || !data.Any())
                {
                    return points;
                }

                // Find max value for Y scaling
                double maxValue = 1000;
                foreach (var p in data)
                {
                    maxValue = Math.Max(maxValue, Math.Max(p.PV, Math.Max(p.EV, p.AC)));
                }
                maxValue *= 1.1; // Add 10% margin

                int count = data.Count;
                double xStep = CanvasWidth / Math.Max(1, count - 1);

                for (int i = 0; i < count; i++)
                {
                    var item = data[i];
                    double val = LineType switch
                    {
                        "PV" => item.PV,
                        "EV" => item.EV,
                        "AC" => item.AC,
                        _ => 0
                    };

                    if ((LineType == "EV" || LineType == "AC") && val == 0 && item.Date > DateTime.Now)
                    {
                        continue; 
                    }

                    double x = i * xStep;
                    double y = CanvasHeight - (val / maxValue) * (CanvasHeight - 20) - 10;

                    if (double.IsNaN(x) || double.IsInfinity(x) || double.IsNaN(y) || double.IsInfinity(y))
                    {
                        continue;
                    }

                    points.Add(new Point(x, y));
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"SCurveToPointsConverter error: {ex.Message}");
            }

            return points;
        }


        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}
