using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddSegmentProvenance : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<float>(
                name: "Confidence",
                table: "VideoSegments",
                type: "real",
                nullable: true);

            migrationBuilder.AddColumn<DateTime>(
                name: "GeneratedAt",
                table: "VideoSegments",
                type: "timestamp with time zone",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "Model",
                table: "VideoSegments",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "Source",
                table: "VideoSegments",
                type: "text",
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "Confidence",
                table: "VideoSegments");

            migrationBuilder.DropColumn(
                name: "GeneratedAt",
                table: "VideoSegments");

            migrationBuilder.DropColumn(
                name: "Model",
                table: "VideoSegments");

            migrationBuilder.DropColumn(
                name: "Source",
                table: "VideoSegments");
        }
    }
}
