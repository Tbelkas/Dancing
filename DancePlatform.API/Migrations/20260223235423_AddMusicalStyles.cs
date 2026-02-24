using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddMusicalStyles : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "MusicalStyles",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    Name = table.Column<string>(type: "text", nullable: false),
                    Description = table.Column<string>(type: "text", nullable: true),
                    DateAdded = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_MusicalStyles", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "DanceMusicalStyles",
                columns: table => new
                {
                    DanceId = table.Column<int>(type: "integer", nullable: false),
                    MusicalStyleId = table.Column<int>(type: "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_DanceMusicalStyles", x => new { x.DanceId, x.MusicalStyleId });
                    table.ForeignKey(
                        name: "FK_DanceMusicalStyles_Dances_DanceId",
                        column: x => x.DanceId,
                        principalTable: "Dances",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_DanceMusicalStyles_MusicalStyles_MusicalStyleId",
                        column: x => x.MusicalStyleId,
                        principalTable: "MusicalStyles",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_DanceMusicalStyles_MusicalStyleId",
                table: "DanceMusicalStyles",
                column: "MusicalStyleId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "DanceMusicalStyles");

            migrationBuilder.DropTable(
                name: "MusicalStyles");
        }
    }
}
