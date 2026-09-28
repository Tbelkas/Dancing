using System;
using System.Collections.Generic;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddGlossary : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "GlossaryTerms",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    StyleId = table.Column<int>(type: "integer", nullable: false),
                    Slug = table.Column<string>(type: "text", nullable: false),
                    Name = table.Column<string>(type: "text", nullable: false),
                    Aliases = table.Column<List<string>>(type: "text[]", nullable: false),
                    Category = table.Column<string>(type: "text", nullable: false),
                    Summary = table.Column<string>(type: "text", nullable: false),
                    Description = table.Column<string>(type: "text", nullable: false),
                    Steps = table.Column<List<string>>(type: "text[]", nullable: false),
                    Tips = table.Column<List<string>>(type: "text[]", nullable: false),
                    Related = table.Column<List<string>>(type: "text[]", nullable: false),
                    Difficulty = table.Column<int>(type: "integer", nullable: false),
                    IsLearnable = table.Column<bool>(type: "boolean", nullable: false),
                    DanceId = table.Column<int>(type: "integer", nullable: true),
                    SortOrder = table.Column<int>(type: "integer", nullable: false),
                    DateAdded = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_GlossaryTerms", x => x.Id);
                    table.ForeignKey(
                        name: "FK_GlossaryTerms_Dances_DanceId",
                        column: x => x.DanceId,
                        principalTable: "Dances",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.SetNull);
                    table.ForeignKey(
                        name: "FK_GlossaryTerms_Styles_StyleId",
                        column: x => x.StyleId,
                        principalTable: "Styles",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "UserLearnedGlossaryTerms",
                columns: table => new
                {
                    UserId = table.Column<int>(type: "integer", nullable: false),
                    GlossaryTermId = table.Column<int>(type: "integer", nullable: false),
                    DateAdded = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_UserLearnedGlossaryTerms", x => new { x.UserId, x.GlossaryTermId });
                    table.ForeignKey(
                        name: "FK_UserLearnedGlossaryTerms_GlossaryTerms_GlossaryTermId",
                        column: x => x.GlossaryTermId,
                        principalTable: "GlossaryTerms",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_UserLearnedGlossaryTerms_Users_UserId",
                        column: x => x.UserId,
                        principalTable: "Users",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_GlossaryTerms_DanceId",
                table: "GlossaryTerms",
                column: "DanceId");

            migrationBuilder.CreateIndex(
                name: "IX_GlossaryTerms_StyleId_Slug",
                table: "GlossaryTerms",
                columns: new[] { "StyleId", "Slug" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_UserLearnedGlossaryTerms_GlossaryTermId",
                table: "UserLearnedGlossaryTerms",
                column: "GlossaryTermId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "UserLearnedGlossaryTerms");

            migrationBuilder.DropTable(
                name: "GlossaryTerms");
        }
    }
}
