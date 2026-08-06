using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddPersonalRoadmaps : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<DateTime>(
                name: "DateModified",
                table: "Roadmaps",
                type: "timestamp with time zone",
                nullable: true);

            migrationBuilder.AddColumn<int>(
                name: "OwnerUserId",
                table: "Roadmaps",
                type: "integer",
                nullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_Roadmaps_OwnerUserId",
                table: "Roadmaps",
                column: "OwnerUserId");

            migrationBuilder.AddForeignKey(
                name: "FK_Roadmaps_Users_OwnerUserId",
                table: "Roadmaps",
                column: "OwnerUserId",
                principalTable: "Users",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Roadmaps_Users_OwnerUserId",
                table: "Roadmaps");

            migrationBuilder.DropIndex(
                name: "IX_Roadmaps_OwnerUserId",
                table: "Roadmaps");

            migrationBuilder.DropColumn(
                name: "DateModified",
                table: "Roadmaps");

            migrationBuilder.DropColumn(
                name: "OwnerUserId",
                table: "Roadmaps");
        }
    }
}
