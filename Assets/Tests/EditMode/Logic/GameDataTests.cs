using System.Linq;
using NUnit.Framework;

namespace Pofi.Tests.Logic
{
    public class GameDataTests
    {
        [Test]
        public void Data_is_valid()
        {
            var errors = TestData.Load().Validate();
            Assert.IsEmpty(errors, string.Join("\n", errors));
        }

        [Test]
        public void Twelve_pets_with_expected_ids()
        {
            var ids = TestData.Load().Pets.Select(p => p.Id).ToArray();
            CollectionAssert.AreEqual(Enumerable.Range(1, 12).Select(i => $"pet_{i:00}").ToArray(), ids);
        }
    }
}
