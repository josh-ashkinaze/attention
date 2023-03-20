/**
 * Fetches the interest over time data from Google Trends for a given keyword and time range,
 * and logs the results in JSON format.
 *
 * @param {string} kw - The keyword to search for.
 * @param {string} start_date - The start date of the search range in YYYY-MM-DD format.
 * @param {string} end_date - The end date of the search range in YYYY-MM-DD format.
 * @param {string} search_type - The search type to filter results by; one of "news", "web", or "youtube".
 */

const googleTrends = require('google-trends-api');

async function fetchInterestOverTime(kw, start_date, end_date, search_type) {
  try {
    const data = await googleTrends.interestOverTime({
      keyword: kw,
      startTime: new Date(start_date),
      endTime: new Date(end_date),
      geo: 'US',
      ...(search_type && search_type !== 'web' ? {property: search_type} : {}),
    });

    const parsedData = JSON.parse(data).default.timelineData;
    const results = parsedData.map(item => {
      return {
        kw: kw,
        value: item.value[0],
        date: new Date(item.time * 1000).toISOString().slice(0, 10),
      };
    });

    console.log(JSON.stringify(results));
  } catch (error) {
    console.error("Error fetching data:", error);
  }
}

// Retrieve command-line arguments
const args = process.argv.slice(2);
if (args.length < 4) {
  console.log("Usage: node gtrends.js <keyword> <start_date> <end_date> <search_type>");
  process.exit(1);
}

const [kw, start_date, end_date, search_type] = args;

fetchInterestOverTime(kw, start_date, end_date, search_type);
