using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace AFMI_Gestion_projet.Data.Migrations
{
    /// <inheritdoc />
    public partial class ResultsIndicators : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "Aggregation",
                table: "Indicators",
                type: "TEXT",
                maxLength: 20,
                nullable: false,
                defaultValue: "Somme");

            migrationBuilder.AddColumn<double>(
                name: "BaselineValue",
                table: "Indicators",
                type: "REAL",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "Level",
                table: "Indicators",
                type: "TEXT",
                maxLength: 20,
                nullable: false,
                defaultValue: "Extrant");

            migrationBuilder.CreateTable(
                name: "IndicatorMeasurements",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    IndicatorId = table.Column<int>(type: "INTEGER", nullable: false),
                    PeriodEnd = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    Value = table.Column<double>(type: "REAL", nullable: false),
                    Sex = table.Column<string>(type: "TEXT", maxLength: 1, nullable: false),
                    AgeGroup = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    Zone = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    Source = table.Column<string>(type: "TEXT", maxLength: 200, nullable: false),
                    Notes = table.Column<string>(type: "TEXT", nullable: false),
                    CreatedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_IndicatorMeasurements", x => x.Id);
                    table.CheckConstraint("CK_IndicatorMeasurements_Sex", "Sex IN ('', 'F', 'M')");
                    table.ForeignKey(
                        name: "FK_IndicatorMeasurements_Indicators_IndicatorId",
                        column: x => x.IndicatorId,
                        principalTable: "Indicators",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "IX_IndicatorMeasurements_IndicatorId_PeriodEnd",
                table: "IndicatorMeasurements",
                columns: new[] { "IndicatorId", "PeriodEnd" });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "IndicatorMeasurements");

            migrationBuilder.DropColumn(
                name: "Aggregation",
                table: "Indicators");

            migrationBuilder.DropColumn(
                name: "BaselineValue",
                table: "Indicators");

            migrationBuilder.DropColumn(
                name: "Level",
                table: "Indicators");
        }
    }
}
