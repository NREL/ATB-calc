# LCOE Calculator Tests
Tests and test data for the LCOE and debt fraction calculators.


## Extracting Test Data
A CSV copy of the ATB data workbook XLSX data is stored in this directory to simplify running tests. Updates to the calculator code and the data workbook structure may require testing data to be updated. To update the test data for all technologies, financial cases, and CRPs, run the following in the root directory of the repo:

```
python -m tests.extract_test_data {PATH-TO-DATA-WORKBOOK}
```
where `{PATH-TO-DATA-WORKBOOK}` is the path to the desired version of the ATB data workbook. Technologies may also be updated individually, e.g.:

```
python -m tests.extract_test_data --tech CommPvProc {PATH-TO-DATA-WORKBOOK}
```
To see a list of all available technologies, run:

```
python -m tests.extract_test_data --help
```