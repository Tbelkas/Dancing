using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddVideoIntakeGate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "QualityFlags",
                table: "Videos",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<float>(
                name: "QualityScore",
                table: "Videos",
                type: "real",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "ReviewNote",
                table: "Videos",
                type: "text",
                nullable: true);

            // MUST default to "approved", not "". Every existing row backfills to this
            // value, and the global query filter keeps only ReviewState == "approved",
            // so an empty default would hide the entire catalogue the moment this ran.
            migrationBuilder.AddColumn<string>(
                name: "ReviewState",
                table: "Videos",
                type: "text",
                nullable: false,
                defaultValue: "approved");

            migrationBuilder.AddColumn<DateTime>(
                name: "ReviewedAt",
                table: "Videos",
                type: "timestamp with time zone",
                nullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_Videos_ReviewState",
                table: "Videos",
                column: "ReviewState");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "IX_Videos_ReviewState",
                table: "Videos");

            migrationBuilder.DropColumn(
                name: "QualityFlags",
                table: "Videos");

            migrationBuilder.DropColumn(
                name: "QualityScore",
                table: "Videos");

            migrationBuilder.DropColumn(
                name: "ReviewNote",
                table: "Videos");

            migrationBuilder.DropColumn(
                name: "ReviewState",
                table: "Videos");

            migrationBuilder.DropColumn(
                name: "ReviewedAt",
                table: "Videos");
        }
    }
}
