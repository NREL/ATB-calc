Note that this code depends on the code in lcoe_calculator

I recommend using `conda develop path_to_lcoe_calculator` to reference those files

Additional dependencies
- numpy
- pandas
- nrel-pysam

To install pysam, run conda install -c nrel nrel-pysam

To run: 
- set the path to the data master file in debt_fraction_calc.py
- run Python debt_fraction_calc.py
- Copy values to the data master as appropriate
    (I don't view setting up an automated write function as worthwhile, since this script should only need to be run 3 or 4 times/year)