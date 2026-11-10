using System;
using System.Collections.Generic;
using System.Linq;
using AFMI_Gestion_projet.Models;

namespace AFMI_Gestion_projet.Services
{
    public class EvmMetrics
    {
        public double BAC { get; set; } // Budget at Completion
        public double PV { get; set; }  // Planned Value
        public double EV { get; set; }  // Earned Value
        public double AC { get; set; }  // Actual Cost
        
        public double CV { get; set; }  // Cost Variance (EV - AC)
        public double SV { get; set; }  // Schedule Variance (EV - PV)
        
        public double CPI { get; set; } // Cost Performance Index (EV / AC)
        public double SPI { get; set; } // Schedule Performance Index (EV / PV)
        
        public double EAC { get; set; } // Estimate at Completion (BAC / CPI)
        public double ETC { get; set; } // Estimate to Complete (EAC - AC)
        public double VAC { get; set; } // Variance at Completion (BAC - EAC)
    }

    public class SCurvePoint
    {
        public DateTime Date { get; set; }
        public string DateLabel { get; set; } = string.Empty;
        public double PV { get; set; }
        public double EV { get; set; }
        public double AC { get; set; }
    }

    public class EvmService
    {
        public EvmMetrics CalculateMetrics(Project project)
        {
            var metrics = new EvmMetrics();
            
            // BAC
            metrics.BAC = project.BudgetGlobal > 0 ? project.BudgetGlobal : project.Tasks.Where(t => t.ParentTaskId == null).Sum(t => t.Budget);
            if (metrics.BAC == 0)
            {
                metrics.BAC = project.Tasks.Sum(t => t.Budget);
            }
            
            // If no tasks, return empty metrics
            if (!project.Tasks.Any())
            {
                metrics.CPI = 1.0;
                metrics.SPI = 1.0;
                metrics.EAC = metrics.BAC;
                metrics.ETC = metrics.BAC;
                return metrics;
            }

            // Task list (only leaf tasks to avoid double counting)
            var leafTasks = GetLeafTasks(project.Tasks.ToList());

            // Calculate current date
            var now = DateTime.Now;

            // EV: Sum of (Task Budget * ProgressPercentage / 100)
            metrics.EV = leafTasks.Sum(t => t.Budget * (t.ProgressPercentage / 100.0));

            // AC: Sum of Task actual costs
            metrics.AC = leafTasks.Sum(t => t.Cost);

            // PV: Sum of Task Planned Values up to today
            metrics.PV = leafTasks.Sum(t => CalculateTaskPV(t, now));

            // CV & SV
            metrics.CV = metrics.EV - metrics.AC;
            metrics.SV = metrics.EV - metrics.PV;

            // CPI
            metrics.CPI = metrics.AC > 0 ? metrics.EV / metrics.AC : 1.0;
            // SPI
            metrics.SPI = metrics.PV > 0 ? metrics.EV / metrics.PV : 1.0;

            // EAC
            metrics.EAC = metrics.CPI > 0 ? metrics.BAC / metrics.CPI : metrics.BAC;
            
            // ETC
            metrics.ETC = Math.Max(0, metrics.EAC - metrics.AC);
            
            // VAC
            metrics.VAC = metrics.BAC - metrics.EAC;

            return metrics;
        }

        public List<SCurvePoint> GetSCurveData(Project project, int intervals = 10)
        {
            var points = new List<SCurvePoint>();
            
            var startDate = project.TargetStartDate ?? DateTime.Now.AddDays(-30);
            var endDate = project.TargetEndDate ?? DateTime.Now.AddDays(30);

            if (startDate >= endDate)
            {
                endDate = startDate.AddDays(30);
            }

            var totalDuration = (endDate - startDate).TotalDays;
            var stepDays = totalDuration / Math.Max(1, intervals);

            var leafTasks = GetLeafTasks(project.Tasks.ToList());

            for (int i = 0; i <= intervals; i++)
            {
                var refDate = startDate.AddDays(stepDays * i);
                
                // Calculate cumulative values at this reference date
                double pvCum = 0;
                double evCum = 0;
                double acCum = 0;

                foreach (var task in leafTasks)
                {
                    // PV cumulative
                    pvCum += CalculateTaskPV(task, refDate);

                    // EV cumulative
                    // Simple model: if refDate is after task completion/current progress date,
                    // we interpolate progress based on target duration, capped by current actual progress if refDate is today
                    if (refDate >= DateTime.Now)
                    {
                        // Future: we don't draw EV/AC for future dates unless it is forecast, 
                        // so we only draw EV up to today's date in S-Curve.
                        // Let's keep EV/AC at current value or leave it empty.
                    }
                    else
                    {
                        evCum += CalculateTaskEVCumulative(task, refDate);
                        acCum += CalculateTaskACCumulative(task, refDate);
                    }
                }

                // If date is in the future, we don't display actual EV and AC (keep them flat or omit, we will keep them flat at current value for now, or just let them end at today)
                bool isFuture = refDate > DateTime.Now;

                points.Add(new SCurvePoint
                {
                    Date = refDate,
                    DateLabel = refDate.ToString("dd/MM/yy"),
                    PV = pvCum,
                    EV = isFuture ? 0 : evCum,
                    AC = isFuture ? 0 : acCum
                });
            }

            // Clean up future points so they don't drop to 0 but aren't plotted on EV/AC
            // In the view, we can just check if EV/AC is 0 to avoid plotting it
            return points;
        }

        private List<ProjectTask> GetLeafTasks(List<ProjectTask> tasks)
        {
            // A leaf task has no subtasks
            var parentIds = tasks.Where(t => t.ParentTaskId != null).Select(t => t.ParentTaskId!.Value).Distinct().ToHashSet();
            return tasks.Where(t => !parentIds.Contains(t.Id)).ToList();
        }

        private double CalculateTaskPV(ProjectTask task, DateTime refDate)
        {
            var start = task.TargetStartDate ?? task.Project?.TargetStartDate ?? refDate.AddDays(-10);
            var end = task.TargetEndDate ?? task.Project?.TargetEndDate ?? refDate.AddDays(10);

            if (start >= end) return task.Budget;

            if (refDate <= start) return 0;
            if (refDate >= end) return task.Budget;

            double totalDays = (end - start).TotalDays;
            double elapsedDays = (refDate - start).TotalDays;

            return task.Budget * (elapsedDays / totalDays);
        }

        private double CalculateTaskEVCumulative(ProjectTask task, DateTime refDate)
        {
            var start = task.ActualStartDate ?? task.TargetStartDate ?? DateTime.Now.AddDays(-10);
            var end = task.ActualEndDate ?? task.TargetEndDate ?? DateTime.Now.AddDays(10);
            
            if (refDate <= start) return 0;

            // Calculate current EV
            double currentEV = task.Budget * (task.ProgressPercentage / 100.0);
            
            if (refDate >= DateTime.Now) return currentEV;

            // Interpolate EV from start to now
            var totalDuration = (DateTime.Now - start).TotalDays;
            if (totalDuration <= 0) return currentEV;

            var elapsed = (refDate - start).TotalDays;
            return currentEV * Math.Min(1.0, elapsed / totalDuration);
        }

        private double CalculateTaskACCumulative(ProjectTask task, DateTime refDate)
        {
            var start = task.ActualStartDate ?? task.TargetStartDate ?? DateTime.Now.AddDays(-10);
            
            if (refDate <= start) return 0;
            if (refDate >= DateTime.Now) return task.Cost;

            // Interpolate actual cost from start to now
            var totalDuration = (DateTime.Now - start).TotalDays;
            if (totalDuration <= 0) return task.Cost;

            var elapsed = (refDate - start).TotalDays;
            return task.Cost * Math.Min(1.0, elapsed / totalDuration);
        }
    }
}
