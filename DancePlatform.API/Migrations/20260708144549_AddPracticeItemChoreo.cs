using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddPracticeItemChoreo : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AlterColumn<int>(
                name: "DanceId",
                table: "PracticeSessionItems",
                type: "integer",
                nullable: true,
                oldClrType: typeof(int),
                oldType: "integer");

            migrationBuilder.AddColumn<int>(
                name: "UserChoreoId",
                table: "PracticeSessionItems",
                type: "integer",
                nullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_PracticeSessionItems_UserChoreoId",
                table: "PracticeSessionItems",
                column: "UserChoreoId");

            migrationBuilder.AddForeignKey(
                name: "FK_PracticeSessionItems_UserChoreos_UserChoreoId",
                table: "PracticeSessionItems",
                column: "UserChoreoId",
                principalTable: "UserChoreos",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_PracticeSessionItems_UserChoreos_UserChoreoId",
                table: "PracticeSessionItems");

            migrationBuilder.DropIndex(
                name: "IX_PracticeSessionItems_UserChoreoId",
                table: "PracticeSessionItems");

            migrationBuilder.DropColumn(
                name: "UserChoreoId",
                table: "PracticeSessionItems");

            migrationBuilder.AlterColumn<int>(
                name: "DanceId",
                table: "PracticeSessionItems",
                type: "integer",
                nullable: false,
                defaultValue: 0,
                oldClrType: typeof(int),
                oldType: "integer",
                oldNullable: true);
        }
    }
}
